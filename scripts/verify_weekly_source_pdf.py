"""Check isolated A4 print artifacts; no network or production application access.

Run after verify_weekly_source_print.cjs:
  python scripts/verify_weekly_source_pdf.py ARTIFACT_ROOT [--baseline OLD_ROOT]
Requires PyMuPDF in the test environment. It does not install dependencies.
"""
import argparse
import json
import re
from pathlib import Path
import fitz


def normalized(text):
    return re.sub(r'\s+', '', text)


def analyze(root, baseline=None):
    report=json.loads((root/'print-report.json').read_text())
    old={entry['file']:entry for entry in json.loads((baseline/'print-report.json').read_text())} if baseline else {}
    results=[];failures=[]
    for item in report:
        document=fitz.open(root/(item['file']+'.pdf'))
        pages=[page.get_text() for page in document]
        text=''.join(pages)
        outside=[]
        for index,page in enumerate(document):
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        box=fitz.Rect(span['bbox'])
                        if box.x0<-.5 or box.y0<-.5 or box.x1>page.rect.width+.5 or box.y1>page.rect.height+.5:
                            outside.append({'page':index+1,'text':span['text']})
        checks={
            'visible_text_retained':normalized(item['expectedText'])==normalized(text),
            'inside_paper':not outside,
            'no_empty_page':all(normalized(page) for page in pages),
            'no_css_overflow':not item['overflow'],
        }
        numbers=item['expectedCases']
        if item['view']=='instructions':
            checks['one_instruction_page']=len(pages)==1
        if item['view']=='daily':
            checks['one_page_per_case']=len(pages)==len(numbers)
            checks['case_order_and_unfragmented_tables']=(len(pages)==len(numbers) and all(
                [number for number in numbers if number in normalized(page)]==[wanted]
                for page,wanted in zip(pages,numbers)))
        if item['view'].startswith('share'):
            checks['map_with_last_card']=numbers[-1] in normalized(pages[-1]) and '全体地図' in normalized(pages[-1])
            checks['no_header_only_or_continuation_page']=all(any(number in normalized(page) for number in numbers) for page in pages)
        if item['file'] in old:
            checks['pre_fix_visible_content_retained']=normalized(item['expectedText'])==normalized(old[item['file']]['expectedText'])
        errors=[name for name,passed in checks.items() if not passed]
        if errors:failures.append({'file':item['file'],'failed':errors})
        results.append({'file':item['file'],'pages':len(pages),'pageCharacters':[len(normalized(page)) for page in pages],
                        'checks':checks,'outsideSpans':outside,'pageText':pages})
    if len(report)!=38:failures.append({'inventory':f'Expected 38 print variants, got {len(report)}'})
    summary={'views':len(report),'pages':sum(entry['pages'] for entry in results),'failures':failures,'results':results,
             'limits':'External maps are not loaded or validated. Physical printing is not performed.'}
    (root/'pdf-analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('--baseline',type=Path)
    args=parser.parse_args();result=analyze(args.root,args.baseline)
    print(json.dumps({key:result[key] for key in ['views','pages','failures']},ensure_ascii=False))
    raise SystemExit(bool(result['failures']))

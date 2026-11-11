# Restore maps on fifteen historical archive pages

## Source route

- Source implementation commit: bf6b1469b3bd1cca2691c06619532c5fdad15374.
- Generated with the reviewed legacy v4 CLI from pinned current/source Git blobs and hash-verified map helpers/GPS. No business export was reconstructed.
- Output reproduces all frozen HTML SHA256 values exactly.

## Verified scope

- 15 dates, 69 cases, 236 restored map roles (59 starts, 59 ends, 68 representatives, 50 single links).
- Existing map values, endpoint JSON objects, representative objects, map panels and JavaScript are preserved. Existing control markup differs only by 85 explicitly approved semantic role-class additions.
- Non-map business bytes, quantity tables, headings, statuses and saved-form links remain unchanged. Ordinary map reader returns the exact expected MapViews.
- Exactly 15 of 797 portal/share files changed. The other 782 files, including fixed forms, navigation, modern repairs and map-alias pages, are byte-identical. No files were added to or removed from portal/share.
- 260630, 260709, 260716 and 260722 remain excluded because their evidence/specification is unresolved.
- Ordinary prepare_archive_maps remains incompatible with retained midpoint versus GPS-end representative policy and fails closed. The common guard was not changed. Runtime adoption is not part of this commit.
- Browser interaction and printing were not performed. No push or publication was performed.

## Generated page SHA256

- portal/archive/260529/index.html: 71680f2c37f94f4ca86f23bd7b4bd9852d9814cbcd622f979fcc0204510c02b4
- portal/archive/260615/index.html: cd5604baccd89363fd5053d44da28a238a09994498c43ee176449180d5d37c86
- portal/archive/260616/index.html: 8a4a8a0572fd71c080fd84a42f578ace637726ad59314e340ff3044c6f5a720d
- portal/archive/260617/index.html: f217eef5c90f036d12c874037523bdc572238a705f1bac279513366e96524b71
- portal/archive/260618/index.html: 2d366ef694c66ec0bd741b8e54996cb3edcfa73bb5c1985987724be4cabbae4e
- portal/archive/260619/index.html: a0d0d1f72be0393b4a1989f110851673498e01d61890fba414fe7b7d7ccd6cfb
- portal/archive/260622/index.html: 7cb25b010f8467a016c2d472ef97a4efce1ee9c1f0c420a0e20d5825bcbdd22f
- portal/archive/260623/index.html: f042323d86ab5bd4f4c93c42784e526a34075ae5b72b37fe7359e5402f9e6476
- portal/archive/260624/index.html: cc85a09f9e630d1a5a7ea9e2a08d19850b2bce48c04306d985be90e73556038b
- portal/archive/260625/index.html: 7756587b17f76ffe817ea6a9b184282bf4ecaa97df65c1b3d1566f4f629d2127
- portal/archive/260629/index.html: 11b6afd7ed71df9f92f8b7901cc29fe1a8bebb500a9d1e5b26dcc18f74ff7c1c
- portal/archive/260701/index.html: 00f7bba605a0bcd27e66e1fe0fd3ed409596f6c9e4dde27e4ffc956a86a7a18a
- portal/archive/260703/index.html: bb216a81cd1f81e4724e8e51ccd1329a87568d2dc3478f6269ca4c9fc027f306
- portal/archive/260714/index.html: 5d0250695559922d4a44a99d0a3116aa661f93854f0502230722d69f9f5b9881
- portal/archive/260721/index.html: 7cf54da594a86946d708cebe14a4067ce23312678f93f5d06bf245ce988a4a3b

Private input manifests, source inventories and candidate reports are excluded from this commit.

# Repository size and optional history cleanup

The pre-cleanup tracked working tree occupied **344,152,088 bytes (328.2 MiB)**.
The portfolio source is approximately **7.9 MB (7.6 MiB)**, excluding ignored
environments, local scratch and generated archives. This is about a **97.7%**
reduction in checked-out tracked content, not in clone size.

The existing Git pack is **84.00 MiB**. Normal commits add a small amount of loose
object data; deleting paths does not remove their historical blobs. The archive
tag and branch intentionally keep every historical commit reachable.

The object audit attributes these unique historical blobs by one recorded path:

| Kind | Unique blobs | Uncompressed bytes | Stored object bytes |
| --- | ---: | ---: | ---: |
| ZIP | 9 | 20,510,798 | 20,234,714 |
| ONNX and external ONNX data | 6 | 34,271,027 | 24,193,515 |

Duplicate copies of identical files share a Git blob, so summing file paths would
overstate history size. Stored sizes include delta representations and cannot be
treated as an exact prediction of savings after a repack. The largest individual
uncompressed objects are three confirmation-exclusion SQLite databases, about
37–39 MB each. One of those consumes roughly 33 MB in the current pack.
See [the object audit](AUDIT.json) for hashes, paths and the largest twenty blobs.

## Separate proposal only: git-filter-repo

A rewrite could materially reduce clone size, but conflicts with retaining the
historical workspace in the same repository. No rewrite was performed.

1. Make and verify an external full mirror or Git bundle containing every branch,
   tag and release source reference. Preserve its checksum in independent storage.
2. Keep an untouched archive repository permanently available. An archive tag in
   the repository being filtered is insufficient: keeping it unchanged retains
   the unwanted blobs; filtering it changes the promised historical reference.
3. In a disposable mirror only, run `git filter-repo --analyze`. Build an explicit
   path/blob removal list from the audit, starting with old ZIPs, unused models and
   obsolete SQLite experiment databases. Retain the root policy model and compact
   final-package weights, and keep the exact final ZIP as a release asset.
4. Review a dry comparison of commits, source trees, tags, authorship and release
   links. Run tests and extracted-package smoke against the resulting source.
   Repack only that disposable mirror and measure actual clone savings.
5. Present the resulting refs, measured savings, external archive location and
   collaborator migration instructions for explicit owner approval. Only then
   consider coordinated force-pushes and re-cloning guidance.

No `git-filter-repo`, force-push, historical squash, remote-branch deletion or
destructive garbage collection was executed during portfolio cleanup.

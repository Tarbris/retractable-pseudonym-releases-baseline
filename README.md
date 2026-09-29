# Retractable pseudonym releases: v1 baseline

This newly authored, AI-assisted baseline is a small offline CSV pseudonymizer, not an established third-party product. It uses Python 3.9+ and the standard library on Linux. All examples concern synthetic data; deterministic seeded pseudonyms are not a claim of irreversible anonymity or regulatory compliance.

Run from this directory:

```
python -m unittest discover -s tests -v
python -m pseudonym export --input INPUT --output OUTPUT --seed demo
```

INPUT contains three UTF-8 CSV files with these exact ordered headers:

```
subjects.csv: row_id,tenant,local_id,name
visits.csv: row_id,tenant,subject_id,category
referrals.csv: row_id,from_tenant,from_id,to_tenant,to_id,note
```

Identifiers, tenant, category and seed use 1–64 ASCII letters, digits, `_` or `-`. Text fields name/note may contain Unicode. `row_id` is a table-local synthetic public row handle, not an entity key. Subjects are uniquely identified by `(tenant,local_id)`, with existing references required from both other tables. The program validates the entire input before creating or changing output files. There is no atomic multi-file publication guarantee for disk/IO errors.

It replaces identity fields with `ps_` plus the complete hexadecimal HMAC-SHA256 of `b"person\0" + compact_ascii_json([tenant,local_id])`, using UTF-8 seed bytes as the HMAC key. It clears name/note, preserving filenames, headers, row order, counts and remaining fields. The same scoped identity receives the same pseudonym across all files. Equal local IDs in different tenants are distinct. Repeated runs using the same seed produce the same output.

## Deliberately absent from v1

There is no `serve` command, database, revision protocol, identity-equivalence link graph, link revocation, transactional update batch, or incremental release patch. The proposed repository change must add those behaviors. The final test confirms that v1 lacks serve; it is a baseline boundary test, and should be replaced with positive serve coverage when implementing the proposed change. Complete new-feature solutions and author feasibility implementations are not published here.

The source was independently authored for the candidate, not copied from benchmark task code, data or tests. License: MIT.

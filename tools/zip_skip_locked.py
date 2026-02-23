import os
import zipfile
import sys

src = os.path.join(os.getcwd(), 'dist', 'iJeery_V5.0')
out = os.path.join(os.getcwd(), 'dist', 'iJeery_V5.0_Portable_skiplocked.zip')

if not os.path.isdir(src):
    print('src-missing')
    sys.exit(2)

skipped = []
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        for f in files:
            path = os.path.join(root, f)
            arcname = os.path.relpath(path, os.path.join(src, '..'))
            try:
                zf.write(path, arcname)
            except Exception as e:
                skipped.append((path, str(e)))
                print(f'skipped:{path}:{e}')

print('zip_created' if os.path.exists(out) else 'zip_failed')
if skipped:
    print('skipped_count=%d' % len(skipped))
    for s in skipped[:20]:
        print('SKIP:', s[0], s[1])

"""Build a clean copy of the app for deployment: dist/cowrie-c2-dist/ and dist/cowrie-c2-dist.tar.gz."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_NAME = 'cowrie-c2-dist'
DIST_ROOT = ROOT / 'dist'
DIST_DIR = DIST_ROOT / DIST_NAME

# Only what the app needs at runtime; tests, the virtualenv, caches and the database stay behind.
INCLUDE_FILES = ['requirements.txt']
INCLUDE_DIRS = ['templates', 'static']
IGNORE = shutil.ignore_patterns('__pycache__', '*.py[cod]', '.*')


def build():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    modules = sorted(p for p in ROOT.glob('*.py') if p.name != Path(__file__).name)
    for source in modules + [ROOT / name for name in INCLUDE_FILES]:
        shutil.copy2(source, DIST_DIR / source.name)
    for name in INCLUDE_DIRS:
        shutil.copytree(ROOT / name, DIST_DIR / name, ignore=IGNORE)

    archive = shutil.make_archive(str(DIST_ROOT / DIST_NAME), 'gztar', root_dir=DIST_ROOT, base_dir=DIST_NAME)
    return DIST_DIR, Path(archive)


if __name__ == '__main__':
    dist_dir, archive = build()
    for path in sorted(p for p in dist_dir.rglob('*') if p.is_file()):
        print(path.relative_to(DIST_ROOT))
    print(f'\nDirectory: {dist_dir}')
    print(f'Archive:   {archive}')

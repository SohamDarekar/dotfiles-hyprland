from __future__ import annotations

import sys

from .app import PhotoPrintWizardApp


def main() -> int:
    app = PhotoPrintWizardApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

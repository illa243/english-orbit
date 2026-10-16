# Included components

English Orbit is an independent application, not an official product of OpenAI,
Anthropic or Google. Each provider requires the user's own account and applicable
subscription or access. Provider terms and limits apply.

The Windows installer includes unmodified standalone CPython, PySide6/Qt,
Shiboken6, psutil, UIAutomation/comtypes, Node.js and official provider CLI packages.
Their copyright and license notices are retained beside the components:

- CPython: `runtime/python/LICENSE.txt`.
- PySide6/Qt/Shiboken6 and Python libraries: `runtime/python/Lib/site-packages`,
  including package metadata and bundled license files. Qt is dynamically linked;
  its libraries and the application's Python sources remain accessible and replaceable.
- Node.js: `runtime/node/LICENSE`.
- Official CLI packages: `tools/node_modules`, including package license/README files.
  Dependency versions and integrity hashes: `tools/package-lock.json`.

Source and build scripts: https://github.com/illa243/english-orbit

Portraits in `assets/avatars` are AI-generated fictional adults, not photographs
of people taken from Pinterest. They illustrate fictional AI conversation partners.

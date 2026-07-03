# Sample Workspace

This folder documents the intended fixture shape for manual demos.

Create a local sample outside the repo when testing scan behavior:

```powershell
mkdir F:\cleanroom-sample\demo\.git
mkdir F:\cleanroom-sample\demo\node_modules
'{}' | Set-Content F:\cleanroom-sample\demo\package.json
'x' | Set-Content F:\cleanroom-sample\demo\node_modules\left-pad.txt
repo-cleanroom scan --root F:\cleanroom-sample --out-dir .cleanroom-sample
```

The scanner does not execute any file in the target workspace.

# PDFium Windows exception investigation

## Finding

The local `Windows fatal exception: access violation` is not a fatal PPView process crash. It is raised during PDFium initialization and caught in a first-chance WinDbg session. The native stack identifies a Trend Micro user-mode security module on the failing worker thread:

```text
ntdll!RtlpUnwindPrologue (read from address 0)
  KERNEL32!RtlVirtualUnwindStub
  TmUmEvt64.dll + 0x3b3a6
  TmUmEvt64.dll + 0x4d154
  TmUmEvt64.dll + 0x4e040
  TmUmEvt64.dll + 0x4230d
  TmUmEvt64.dll + 0x61e52
  tmmon64.dll + 0x13c6 ...
  GDIPLUS!BackgroundThreadStartup
  GDIPLUS!GdiplusStartup
  pdfium!FPDF_InitLibraryWithConfig + 0xfd
  libffi_8!ffi_prep_go_closure
```

`TmUmEvt64.dll` was loaded from the Trend Micro `tmumh` directory and its Authenticode signature is valid for Trend Micro, Inc. The exception attempts to read a null address while Windows unwinds a stack through the injected Trend Micro callback. PDFium initialization starts this GDI+ background thread; the thread's stack then enters the third-party security modules. This points to a local interaction with injected endpoint-security code, rather than a faulting PPView Python frame or a failure in pypdfium2's Python binding. It does not prove the exact Trend Micro defect or exclude an interaction with PDFium's GDI+ startup.

## Reproduction and cross-checks

On the affected Windows development machine with CPython 3.11.5 and pypdfium2 5.14.0:

- Plain Python and importing PySide6 alone are quiet. A normal PDFium import without faulthandler is also quiet, but CDB still catches the same first-chance `0xC0000005` exception during that import. This confirms faulthandler reports the existing exception rather than creating it.
- Importing PDFium with Python faulthandler enabled prints the access-violation trace at `FPDF_InitLibraryWithConfig`, then exits with code 0.
- Pytest's normal faulthandler plugin prints the same trace. Running the focused pytest file with that plugin disabled passes without the message; this is a comparison only, not a project workaround.
- WinDbg/CDB first-chance capture locates the null read in `ntdll!RtlpUnwindPrologue` while unwinding through signed Trend Micro modules on a GDI+ background thread started by PDFium initialization.
- Existing and current repeated-render checks complete 50 renders, release documents, and exit normally. The packaged application has also previously launched and rendered PDFs successfully; v0.2.2 package smoke checks exercise this again.
- GitHub Actions runs the same diagnostic matrix on a clean hosted Windows runner. Compare its run log with the local result; the hosted runner has no Trend Micro module loaded.

The exception has not been suppressed, faulthandler remains enabled under pytest, and PDFium remains in use. If the same native stack appears on a clean GitHub runner without the Trend Micro modules, treat that as a new unresolved native defect and pause broader testing until investigated.

Repeat the native capture with `./scripts/pdfium_native_trace.ps1` when CDB is available. It captures the first-chance exception without enabling faulthandler and writes `build/pdfium-native-trace.log`; that raw log contains local paths and loaded module information, so review it before sharing outside the machine.

## Limits

The fault was captured on the Trend Micro protected development machine, not on an unprotected machine. CDB stopped at the first-chance exception to capture the stack; allowing normal execution outside the debugger continues to exit successfully. The evidence locates the immediate faulting path in third-party injected code, but does not identify its internal source line (vendor symbols are unavailable) or rule out a compatibility defect between that hook and GDI+ startup. No software-specific exception handler or security exclusion was added.

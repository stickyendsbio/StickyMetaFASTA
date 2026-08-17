# Sticky MetaFASTA v1.0.0

**NCBI metadata scanner & FASTA downloader**

Developed and published by **Sticky Ends Bio Private Limited, Kannur, Kerala, India**.

Sticky MetaFASTA scans NCBI Nucleotide GenBank records, reports availability
and values for selected metadata, and exports records satisfying either an
**all selected fields** or **at least one selected field** rule. Qualifying
records can be saved as CSV reports or as synchronized FASTA and CSV files.

## Main functionality

- NCBI Nucleotide searches using Entrez
- Optional organism and nucleotide-length filters
- Metadata availability and value summaries
- ALL or AT LEAST ONE metadata matching
- CSV report generation
- Synchronized FASTA and metadata CSV export
- Publication/direct-submission classification from GenBank references
- Windows graphical interface
- Ubuntu command-line interface

Metadata are read from the nucleotide GenBank record. Sticky MetaFASTA does
not separately query linked BioSample records.

## Download and run on Windows

1. Open the **Releases** page for this GitHub repository.
2. Download `Sticky-MetaFASTA-v1.0.0-Windows.zip`.
3. Extract the complete ZIP folder. Do not remove the `_internal` folder.
4. Open `Sticky MetaFASTA v1.0.0.exe`.

The Windows release includes Python and its required runtime files, so an
ordinary Windows user does not need to install Python.

An internet connection and an email ID registered with NCBI are required for
NCBI searches. The NCBI API key is optional.

## Run from source

Python 3.10 or later is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_gui.py
```

Ubuntu users can install the package and run its command-line interface:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
sticky-metafasta
```

## Build the Windows application

Double-click `build_windows_exe.bat`, or run:

```powershell
.\build_windows_exe.bat
```

The current PyInstaller configuration produces:

```text
dist/
└── Sticky MetaFASTA v1.0.0/
    ├── Sticky MetaFASTA v1.0.0.exe
    └── _internal/
```

For complete build and release-package instructions, see
[`docs/BUILDING.md`](docs/BUILDING.md).

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Citations and third-party software

See [`CITATIONS.md`](CITATIONS.md) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Sticky MetaFASTA is independently developed and is not affiliated with,
sponsored by, or endorsed by NCBI.

## Licence

Sticky MetaFASTA is licensed under the **GNU General Public License version 3
or later**. See [`LICENSE`](LICENSE).

## Feedback and problems

Feedback and problem reports may be sent to **stickyendsbio@gmail.com**.


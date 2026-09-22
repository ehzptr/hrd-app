# HrdApp app

## Architecture

The application is organized into independent processing and presentation
layers:

- `src/attendance` cleans scan data, calculates daily attendance, and derives
  attendance analytics.
- `src/application` contains configurable HR, leave, payroll, employee-master,
  and sales rules.
- `src/services` loads files and orchestrates the processing pipeline.
- `src/ui` contains the Flet page, typed view models, and upload/config/results
  panels. Results tables use `flet-datatable2` for sticky headers, fixed
  columns, and horizontal scrolling.
- `src/reporting` renders Excel audit workbooks. Shared styles and template
  helpers are in `styles.py` and `excel_utils.py`.

Generated workbooks include a `PROVENANCE` sheet containing the UTC generation
timestamp, report period, source filenames, configuration hash, row counts,
and caller-provided metadata. This provides an audit trail without changing
the calculation data.

## Run the app

### uv

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/).

## Build the app

### Android

```bash
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```bash
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```bash
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```bash
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```bash
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

### Web

```bash
flet build web -v
```

For more details on building Web app, refer to the [Web Packaging Guide](https://flet.dev/docs/publish/web/).

src/
  application/
    config.py
    employee_master.py
    leave.py
    payroll.py
    sales.py

  attendance/
    parser.py
    engine.py
    analytics.py

  services/
    file_engine.py
    pipeline.py
    models.py              # new: PipelineRequest/PipelineResult

  reporting/
    excel_report.py
    payslip.py

  ui/
    components.py          # Shared Flet controls
    formatters.py          # Presentation formatting
    view_models.py         # Typed UI state models
    panels/
      upload.py            # Uploads and template downloads
      config.py            # Schedule, scoring and payroll inputs
      results.py           # Results presentation
    page.py                # Page composition
    sidebar.py             # Sidebar composition
    state.py               # UI event orchestration

  reporting/
    models.py              # ReportData and provenance metadata
    styles.py              # Shared workbook styles
    excel_utils.py         # Shared table/template helpers
    excel_report.py        # Audit workbook renderer
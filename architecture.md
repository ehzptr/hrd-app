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
    common/
      formatters.py
      view_models.py       # new
    flet_app/
      app.py               # new Flet entrypoint
      page_state.py        # new
      upload_panel.py
      config_panel.py
      results_view.py
      tables.py
      charts.py

  hr_nicegui/              # temporary compatibility package
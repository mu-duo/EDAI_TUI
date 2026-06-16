Command Reference
=================

EDAI includes **184 EDA commands** organized by subsystem. Below is a
reference grouped by functional area.

Config
------

Commands for flow initialization and configuration.

* ``flow_init`` — Initialize the EDA flow.
* ``db_init`` — Initialize the design database.
* ``flow_config`` — Set flow-level configuration options.
* ``flow_init_flow`` — Initialize from a saved flow configuration.
* ``flow_save_config`` — Save current flow configuration.

Database
--------

Commands for loading and saving design data.

* ``idb_init`` — Initialize the intermediate database.
* ``tech_lef_init`` — Load technology LEF file.
* ``def_init`` — Load DEF file.
* ``verilog_init`` — Load Verilog netlist.
* ``def_save`` — Save design to DEF format.
* ``netlist_save`` — Save design to Verilog netlist.
* ``gds_save`` — Save design to GDS format.
* ``idb_gds_save`` — Save GDS via intermediate database.

Floorplan
---------

* ``floorplan_init`` — Initialize floorplan.
* ``set_die_area`` — Set die area dimensions.
* ``floorplan_auto`` — Auto-generate floorplan.

PDN (Power Delivery Network)
----------------------------

* ``create_grid`` — Create a power grid on a specified layer.
* ``create_stripe`` — Create power stripes.
* ``connect_two_layer`` — Connect PDN between two layers.
* ``connect_macro_pdn`` — Connect macro pins to PDN.
* ``pdn_connect`` — General PDN connectivity.
* ``pdn_report`` — Report PDN configuration.
* ``pdn_reroute`` — Reroute PDN connections.

Placement (iPL)
---------------

* ``run_placer`` — Run full placement.
* ``run_filler`` — Insert filler cells.
* ``placer_run_gp`` — Run global placement.
* ``placer_run_dp`` — Run detailed placement.
* ``placer_run_bu`` — Run bottom-up placement.
* ``placer_run_co`` — Run cluster-oriented placement.
* ``placer_run_raw`` — Run raw/unconstrained placement.
* ``placer_run_random`` — Run random placement.
* ``placer_init_legalizer`` — Initialize legalizer.
* ``placer_run_legalizer_pause`` — Run legalizer (pause mode).
* ``placer_run_legalizer_resume`` — Resume legalizer.
* ``placer_set_io_pin`` — Set I/O pin constraints.
* ``placer_check_density`` — Check placement density.
* ``report_placement`` — Report placement results.

Clock Tree Synthesis (CTS)
--------------------------

* ``run_cts`` — Run clock tree synthesis.
* ``run_cts_flow`` — Run CTS with flow integration.
* ``run_cts_clustering`` — Run CTS with clustering.
* ``run_cts_sink_clustering`` — Run sink clustering CTS.
* ``cts_report`` — Report CTS results.

Routing (iRT)
-------------

* ``run_rt`` — Run global and detailed routing.
* ``run_ert`` — Run enhanced routing.
* ``run_rt_flow`` — Run routing with flow integration.
* ``run_rt_flow_ert`` — Run enhanced routing with flow.
* ``rt_get_congestion`` — Get congestion data.
* ``rt_report`` — Report routing results.
* ``rt_report_wire_length`` — Report wire length details.
* ``rt_report_via`` — Report via usage.

Static Timing Analysis (STA — iSTA)
-----------------------------------

* ``run_sta`` — Run static timing analysis.
* ``read_liberty`` — Read Liberty timing library.
* ``read_sdc`` — Read SDC timing constraints.
* ``read_spef`` — Read SPEF parasitics.
* ``report_timing`` — Generate timing report.
* ``report_timing_derate`` — Report timing with derating.
* ``report_constraint`` — Report constraint coverage.
* ``report_worst_paths`` — Report worst timing paths.
* ``sta_init`` — Initialize STA engine.
* ``set_timing_corner`` — Set timing analysis corner.
* ``set_analysis_mode`` — Set analysis mode (single/multi-corner).

Power Analysis (iPA)
--------------------

* ``run_power`` — Run power analysis.
* ``report_power`` — Generate power report.
* ``report_ir_drop`` — Report IR drop analysis.
* ``run_power_rail`` — Run power rail analysis.
* ``run_dynamic_power`` — Run dynamic power analysis.
* ``run_leakage_power`` — Run leakage power analysis.
* ``set_activity_factor`` — Set switching activity factor.
* ``pa_init`` — Initialize power analysis.

Timing Optimization (iTO)
-------------------------

* ``run_to`` — Run timing optimization.
* ``run_to_setup`` — Run setup timing optimization.
* ``run_to_hold`` — Run hold timing optimization.
* ``to_config`` — Configure timing optimization.
* ``to_report`` — Report timing optimization results.

Net Optimization (iNO)
----------------------

* ``run_no_fixfanout`` — Fix high-fanout nets.
* ``no_config`` — Configure net optimization.
* ``no_report`` — Report net optimization results.

DRC (Design Rule Checking — iDRC)
----------------------------------

* ``run_drc`` — Run design rule checking.
* ``check_def`` — Check DEF file for DRC violations.
* ``save_drc`` — Save DRC results.
* ``drc_init`` — Initialize DRC engine.
* ``drc_config`` — Configure DRC rules.
* ``drc_report`` — Report DRC violations.
* ``drc_mark_fixed`` — Mark DRC violations as fixed.
* ``add_drc_black_cell`` — Exclude cells from DRC checking.

ECO (Engineering Change Order)
------------------------------

* ``eco_repair_via`` — Repair via ECO changes.
* ``eco_repair_pin`` — Repair pin connection ECO.
* ``eco_repair_wire`` — Repair wire ECO.
* ``eco_repair_tapevia`` — Repair taper via ECO.

GUI
---

* ``gui_start`` — Start the GUI viewer.
* ``gui_show`` — Display current design in GUI.
* ``gui_show_idb`` — Display design from database.
* ``gui_set_display`` — Configure GUI display settings.
* ``capture_design`` — Capture design screenshot.
* ``gui_close`` — Close the GUI.
* ``gui_banner`` — Show GUI status banner.

Report
------

* ``report_db`` — Report database summary.
* ``report_wirelength`` — Report wire length statistics.
* ``report_congestion`` — Report routing congestion.
* ``report_utilization`` — Report cell utilization.

PNP (Pin Placement)
-------------------

* ``run_pnp`` — Run pin placement optimization.
* ``pnp_report`` — Report pin placement results.

Vectorization
-------------

* ``vectorization_init`` — Initialize vectorization.
* ``vectorization_run`` — Run vectorization extraction.
* ``vectorization_save_memory`` — Save vectorization data.
* ``vectorization_load_memory`` — Load vectorization data.

Eval
----

* ``eval_init`` — Initialize evaluation engine.
* ``eval_flow`` — Evaluate flow metrics.
* ``eval_flow_parallel`` — Evaluate flow in parallel.

Feature
-------

* ``feature_extract`` — Extract design features.
* ``feature_extract_parallel`` — Extract features in parallel.
* ``feature_select`` — Select features for analysis.
* ``feature_dump`` — Dump extracted features.

Notification
------------

* ``send_notification`` — Send EDA flow notification.
* ``send_notification_to`` — Send notification to specific target.
* ``get_notification`` — Retrieve pending notifications.
* ``get_notification_by_type`` — Retrieve notifications by category.
* ``mark_notification_read`` — Mark notification as read.

Contest
-------

* ``run_contest`` — Run design contest evaluation.
* ``contest_init`` — Initialize contest environment.
* ``contest_config`` — Configure contest parameters.
* ``contest_report`` — Report contest results.

Other
-----

* ``netlist_analysis`` — Analyze netlist properties.
* ``netlist_evaluation`` — Evaluate netlist quality.
* ``netlist_flow`` — Run netlist-based flow.
* ``netlist_flow_single`` — Run single netlist flow step.
* ``message`` — Print EDA message.
* ``message_get`` — Retrieve stored messages.
* ``message_set`` — Store a message.
* ``error_get`` — Retrieve error messages.
* ``collect_metric`` — Collect a metric value.
* ``metric_report`` — Report collected metrics.
* ``metric_export`` — Export metrics to file.

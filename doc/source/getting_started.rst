Getting Started
===============

Prerequisites
-------------

* Python 3.10 or later.
* An OpenAI-compatible API key (optional for simulation mode).

Installation
------------

Install EDAI from source:

.. code-block:: bash

   git clone https://github.com/tanlinfeng/EDAI_TUI.git
   cd EDAI_TUI
   pip install -r requirements.txt
   pip install -e .

For development (includes test and lint tools):

.. code-block:: bash

   pip install -r requirements-dev.txt

Configuration
-------------

Create a ``.env`` file in the project root or let EDAI generate one
for you:

.. code-block:: bash

   genenv

Edit the file to set your LLM provider:

.. code-block:: ini

   LLM_BASE_URL="https://api.deepseek.com"
   LLM_MODEL_ID="deepseek-chat"
   LLM_API_KEY="sk-..."

If you only want to use simulation mode (no real LLM required), you
can skip the API key — EDAI will still start and process Tcl commands
directly.

Running EDAI
------------

Start the interactive shell:

.. code-block:: bash

   edai

You will see the IPython prompt with EDAI extensions loaded::

    ┌─────────────────────────────────────────┐
    │  EDAI v0.1.0 — LLM-driven EDA TUI      │
    │  Type Tcl commands, Python, or English. │
    └─────────────────────────────────────────┘

    In [1]:

Try some commands:

.. code-block:: text

    In [1]: read_liberty -path ./lib/slow.lib
    [simulated] Data loaded successfully.

    In [2]: run_placer -max_density 0.7
    [simulated] Run completed successfully.

    In [3]: report_timing -path_type max
    [simulated] Timing report generated.

    In [4]: please set up the design with the liberty file and run STA
    >> Running: read_liberty -path ./lib/slow.lib
    >> Running: read_sdc -path ./constraints/top.sdc
    >> Running: run_sta
    [simulated] STA completed. Worst slack: -0.23

Generating a .env File
----------------------

The ``genenv`` command creates a fresh ``.env`` from a template:

.. code-block:: bash

   genenv                   # uses the deepseek template
   genenv --template openai  # uses the OpenAI template
   genenv --force            # overwrite existing .env

What's Next
-----------

* Read the :doc:`usage` guide for detailed walkthroughs.
* Browse the :doc:`commands` reference for all available Tcl commands.
* See :doc:`features` for a full overview of capabilities.

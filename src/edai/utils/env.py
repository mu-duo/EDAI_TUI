from __future__ import annotations

from pathlib import Path


def generate_env_file(force: bool = False, template: str = "deepseek") -> None:
    """Generate a ``.env`` file in the working directory.

    Args:
        force: Overwrite an existing ``.env`` file if ``True``.
        template: One of ``"deepseek"``, ``"openai"``, or anything else for a blank template.
    """
    env_path = Path(".env")
    if env_path.exists() and not force:
        print(".env file already exists. Skipping generation.")
        return

    with open(env_path, "w") as f:
        if template == "deepseek":
            f.write('LLM_BASE_URL="https://api.deepseek.com"\n')
            f.write('LLM_MODEL_ID="deepseek-v4-flash"\n')
            f.write('LLM_API_KEY="sk-..."\n')
            f.write("\n")
            f.write(
                '# Test toggle — set to "true" to run integration tests against the real API.\n'
            )
            f.write('# When unset or "false" the test suite uses mocks / skips real-API tests.\n')
            f.write("EDAI_TEST_REAL_API=false\n")
        elif template == "openai":
            f.write('LLM_BASE_URL="https://api.openai.com/v1"\n')
            f.write('LLM_MODEL_ID="gpt-4o"\n')
            f.write('LLM_API_KEY="sk-..."\n')
            f.write("\n")
            f.write(
                '# Test toggle — set to "true" to run integration tests against the real API.\n'
            )
            f.write('# When unset or "false" the test suite uses mocks / skips real-API tests.\n')
            f.write("EDAI_TEST_REAL_API=false\n")
        else:
            f.write("# Custom .env template\n")
            f.write("# Set LLM_BASE_URL, LLM_MODEL_ID, and LLM_API_KEY as needed.\n")
            f.write('LLM_BASE_URL=""\n')
            f.write('LLM_MODEL_ID=""\n')
            f.write('LLM_API_KEY=""\n')
            f.write("\n")
            f.write(
                '# Test toggle — set to "true" to run integration tests against the real API.\n'
            )
            f.write('# When unset or "false" the test suite uses mocks / skips real-API tests.\n')
            f.write("EDAI_TEST_REAL_API=false\n")

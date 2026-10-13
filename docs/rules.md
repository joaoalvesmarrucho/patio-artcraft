# The three rules

Every skill in this repo follows the same three rules. A studio owner should be able to say them in one breath.

## 1. One job, one folder, two roots

Each job lives in one project folder. The Craft app's MCP server is started with that folder as the read root and `out/` as the write root. `patio_artcraft.py new-project` creates the folder; `serve` prints the configuration; `serve --write-config` writes it for the MCP client to launch. `serve --run` starts the server directly, with the roots set. The agent never widens them and never asks for a shared client drive.

## 2. Files come in by copy

Source files arrive through `bring`, which copies them into `sources/` and logs the hash. Never a link, never a shortcut. The studio's own earlier projects can be reopened freely; a project folder that arrived from outside the studio gets a person's look first.

## 3. Only pinned official releases, installed on purpose

`setup` downloads the official storytold release named in `pins/`, verifies its hash before unzipping, and records the version. It runs once, with a person present, not during a job. Updating means Patio changes the pin, the studio reruns `setup`, and the project record shows the new version.

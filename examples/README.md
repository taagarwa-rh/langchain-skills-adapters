# Examples

## Prerequisites

- Install the extras to run examples
  
    ```sh
    uv sync --extra examples
    ```

- Install playwright (if you haven't already)

    ```sh
    uv run playwright install
    ```

- Set an OpenAI API key in your environment
  
    ```sh
    export OPENAI_API_KEY=your-api-key
    ```
    - You can also update the model with your preferred Langchain `BaseChatModel`

## [Middleware Usage](./middleware_usage.py)

This example shows how to use the `SkillsMiddleware` to integrate skills into your Langchain agent.

Run it with the following command:

```sh
uv run examples/middleware_usage.py
```

## [Dynamic Tool Registration](./dynamic_tool_registration.py)

This example shows how tools can be dynamically registered as skills are activated.

The skills in [browser-skills](./browser-skills/) each have a set of tools defined in their `allowed-tools` frontmatter field.
As the skills are activated, those tools get added to the agent's toolkit.
The example question only uses one of those skills, with a subset of tools activated, to demonstrate this behavior.

Run it with the following command:

```sh
uv run examples/dynamic_tool_registration.py
```

## [Tool Usage](./tool_usage.py)

This example shows how to use the `SkillsTool` to integrate skills into your Langchain agent.

Run it with the following command:

```sh
uv run examples/tool_usage.py
```

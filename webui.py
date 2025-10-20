"""
OpenManus Web UI
A Gradio-based web interface for OpenManus agent system
"""

import asyncio
import argparse
from typing import List, Tuple
import gradio as gr

from app.agent.manus import Manus
from app.logger import logger
from app.config import config


# Language translations
TRANSLATIONS = {
    "ja": {
        "title": "🤖 OpenManus - AIエージェントシステム",
        "description": """
OpenManusは、複数のツールを使用してさまざまなタスクを解決できる多機能AIエージェントです。
以下にリクエストを入力して、OpenManusに処理を任せましょう！

**機能:**
- 🌐 Webブラウジングと検索
- 💻 コード実行と分析
- 📝 ファイル操作
- 🔧 マルチツール統合
        """,
        "config_title": "⚙️ 設定",
        "config_content": """
**現在の設定:**
- モデル: `{model}`
- ワークスペース: `{workspace}`
- 最大ステップ数: `20`

設定を変更するには、`config/config.toml`を編集してください
        """,
        "chat_label": "チャット履歴",
        "input_label": "メッセージ",
        "input_placeholder": "ここにリクエストを入力してください... (例: '最新のAIニュースを検索して')",
        "send_button": "送信 🚀",
        "clear_button": "履歴をクリア 🗑️",
        "examples_label": "💡 サンプルプロンプト",
        "examples": [
            ["AIエージェントに関する最新ニュースを検索して"],
            ["フィボナッチ数を生成するPythonスクリプトを作成して"],
            ["workspace/example.txtのデータを分析して"],
            ["https://github.com/FoundationAgents/OpenManus を閲覧してプロジェクトを要約して"],
            ["簡単な電卓をPythonで書いてworkspace/calculator.pyに保存して"],
        ],
        "footer": """
---
**注意:** OpenManusは複雑なリクエストの処理に時間がかかる場合があります。
お待ちいただき、同時に複数のリクエストを送信しないでください。

[GitHub](https://github.com/FoundationAgents/OpenManus) |
[ドキュメント](https://github.com/FoundationAgents/OpenManus/blob/main/README_ja.md)
        """,
        "processing": "🤔 リクエストを処理中...",
        "completed": "✅ タスク完了！\n\n{result}",
        "completed_simple": "✅ タスクが正常に完了しました！",
        "error": "❌ エラー: {error}",
        "already_processing": "⚠️ 既にリクエストを処理中です。お待ちください...",
        "language_label": "言語 / Language"
    },
    "en": {
        "title": "🤖 OpenManus - AI Agent System",
        "description": """
OpenManus is a versatile AI agent that can solve various tasks using multiple tools.
Enter your request below and let OpenManus handle it for you!

**Features:**
- 🌐 Web browsing and searching
- 💻 Code execution and analysis
- 📝 File operations
- 🔧 Multi-tool integration
        """,
        "config_title": "⚙️ Configuration",
        "config_content": """
**Current Settings:**
- Model: `{model}`
- Workspace: `{workspace}`
- Max Steps: `20`

To change settings, edit `config/config.toml`
        """,
        "chat_label": "Chat History",
        "input_label": "Your Message",
        "input_placeholder": "Enter your request here... (e.g., 'Search for the latest AI news')",
        "send_button": "Send 🚀",
        "clear_button": "Clear History 🗑️",
        "examples_label": "💡 Example Prompts",
        "examples": [
            ["Search for the latest news about AI agents"],
            ["Create a Python script that generates Fibonacci numbers"],
            ["Analyze the data in workspace/example.txt"],
            ["Browse https://github.com/FoundationAgents/OpenManus and summarize the project"],
            ["Write a simple calculator in Python and save it to workspace/calculator.py"],
        ],
        "footer": """
---
**Note:** OpenManus may take some time to process complex requests.
Please be patient and avoid sending multiple requests simultaneously.

[GitHub](https://github.com/FoundationAgents/OpenManus) |
[Documentation](https://github.com/FoundationAgents/OpenManus/blob/main/README.md)
        """,
        "processing": "🤔 Processing your request...",
        "completed": "✅ Task completed!\n\n{result}",
        "completed_simple": "✅ Task completed successfully!",
        "error": "❌ Error: {error}",
        "already_processing": "⚠️ Already processing a request. Please wait...",
        "language_label": "Language / 言語"
    }
}


class WebUI:
    """WebUI controller for OpenManus"""

    def __init__(self, language="ja"):
        self.agent = None
        self.chat_history: List[Tuple[str, str]] = []
        self.is_processing = False
        self.language = language

    def get_text(self, key: str, **kwargs) -> str:
        """Get translated text for the current language"""
        text = TRANSLATIONS[self.language].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    async def initialize_agent(self):
        """Initialize the Manus agent"""
        if self.agent is None:
            logger.info("Initializing Manus agent...")
            self.agent = await Manus.create()
            logger.info("Manus agent initialized successfully")

    async def process_message(self, message: str, history: List[Tuple[str, str]]):
        """Process user message and return response"""
        if not message.strip():
            yield history, ""
            return

        if self.is_processing:
            yield history + [(message, self.get_text("already_processing"))], ""
            return

        try:
            self.is_processing = True

            # Initialize agent if not already done
            await self.initialize_agent()

            # Add user message to history
            history.append((message, self.get_text("processing")))
            yield history, ""

            # Process the request
            logger.info(f"Processing request: {message}")
            result = await self.agent.run(message)

            # Update the last message with the result
            if result:
                response = self.get_text("completed", result=result)
            else:
                response = self.get_text("completed_simple")

            history[-1] = (message, response)

        except Exception as e:
            error_msg = self.get_text("error", error=str(e))
            logger.error(f"Error processing message: {e}")
            if history and history[-1][0] == message:
                history[-1] = (message, error_msg)
            else:
                history.append((message, error_msg))

        finally:
            self.is_processing = False

        yield history, ""

    async def cleanup(self):
        """Cleanup agent resources"""
        if self.agent:
            await self.agent.cleanup()
            self.agent = None


def create_gradio_interface(webui: WebUI):
    """Create and configure the Gradio interface"""

    with gr.Blocks(
        title="OpenManus - AI Agent System",
        theme=gr.themes.Soft(),
        css="""
        .container {max-width: 1200px; margin: auto;}
        .header {text-align: center; padding: 20px;}
        .chat-container {height: 600px;}
        """
    ) as demo:

        # Language selector
        with gr.Row():
            language_selector = gr.Radio(
                choices=[("日本語", "ja"), ("English", "en")],
                value="ja",
                label=webui.get_text("language_label"),
                interactive=True
            )

        # Header
        header_md = gr.Markdown(webui.get_text("description"))
        title_md = gr.Markdown(f"# {webui.get_text('title')}")

        # Configuration info
        with gr.Accordion(webui.get_text("config_title"), open=False) as config_accordion:
            model_name = config.llm.get('default').model if config.llm.get('default') else 'Not configured'
            config_md = gr.Markdown(
                webui.get_text("config_content", model=model_name, workspace=str(config.workspace_root))
            )

        # Chat interface
        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label=webui.get_text("chat_label"),
                    height=500,
                    show_copy_button=True,
                    avatar_images=(None, "assets/logo.jpg"),
                    type="tuples"
                )

                with gr.Row():
                    msg = gr.Textbox(
                        label=webui.get_text("input_label"),
                        placeholder=webui.get_text("input_placeholder"),
                        lines=3,
                        scale=4
                    )
                    submit_btn = gr.Button(webui.get_text("send_button"), variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button(webui.get_text("clear_button"), size="sm")

        # Examples
        examples_label = gr.Markdown(f"### {webui.get_text('examples_label')}")
        examples_component = gr.Examples(
            examples=webui.get_text("examples"),
            inputs=msg
        )

        # Footer
        footer_md = gr.Markdown(webui.get_text("footer"))

        # Language change handler
        def change_language(lang):
            webui.language = lang
            model_name = config.llm.get('default').model if config.llm.get('default') else 'Not configured'
            return [
                gr.update(value=f"# {webui.get_text('title')}"),
                gr.update(value=webui.get_text("description")),
                gr.update(label=webui.get_text("config_title")),
                gr.update(value=webui.get_text("config_content", model=model_name, workspace=str(config.workspace_root))),
                gr.update(label=webui.get_text("chat_label")),
                gr.update(label=webui.get_text("input_label"), placeholder=webui.get_text("input_placeholder")),
                gr.update(value=webui.get_text("send_button")),
                gr.update(value=webui.get_text("clear_button")),
                gr.update(value=f"### {webui.get_text('examples_label')}"),
                gr.update(value=webui.get_text("footer"))
            ]

        language_selector.change(
            change_language,
            inputs=[language_selector],
            outputs=[title_md, header_md, config_accordion, config_md, chatbot, msg, submit_btn, clear_btn, examples_label, footer_md]
        )

        # Event handlers
        def respond(message, chat_history):
            """Wrapper for async message processing"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async_gen = webui.process_message(message, chat_history)
                for result in loop.run_until_complete(async_to_sync_generator(async_gen)):
                    yield result
            finally:
                loop.close()

        async def async_to_sync_generator(async_gen):
            """Convert async generator to list for sync iteration"""
            results = []
            async for item in async_gen:
                results.append(item)
            return results

        msg.submit(
            respond,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )

        submit_btn.click(
            respond,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )

        clear_btn.click(
            lambda: ([], ""),
            outputs=[chatbot, msg]
        )

    return demo


def main():
    """Main entry point for the WebUI"""
    parser = argparse.ArgumentParser(description="OpenManus Web UI")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to bind the server to (default: 7860)"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public shareable link"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="ja",
        choices=["ja", "en"],
        help="Default language (default: ja)"
    )
    args = parser.parse_args()

    # Create WebUI instance with specified language
    webui = WebUI(language=args.lang)

    # Create and launch Gradio interface
    demo = create_gradio_interface(webui)

    logger.info(f"Starting OpenManus Web UI on http://{args.host}:{args.port}")

    try:
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down Web UI...")
    finally:
        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(webui.cleanup())
        loop.close()


if __name__ == "__main__":
    main()

from ai_gradio.integrated_gradio import build_interface

if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        # share=True,
        show_error=True
    ) 
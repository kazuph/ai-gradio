from ai_gradio.integrated_gradio import build_interface

def main():
    demo = build_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        # share=True,
        show_error=True
    )

if __name__ == "__main__":
    main() 
import gradio as gr

javascript = """
function copyToClipboard() {
    var img = Array.from(document.querySelectorAll('.output-image img') || []).filter(img => img.offsetParent)[0];
    if (!img) {
        return;
    }
    fetch(img.src)
    .then(response => response.blob())
    .then(blob => {
        const item = new ClipboardItem({ "image/png": blob });
        navigator.clipboard.write([item]);
    })
    .catch(console.error);
}
"""

class OutputImage:
    def __init__(self, app_config, transfer_target_lang_key=None):
        self.app_config = app_config
        self.transfer_button = None
        self.output_image = None
        self.output_image_path = None
        self.transfer_target_lang_key = transfer_target_lang_key

    def layout(self):
        lang_util = self.app_config.lang_util
        if self.transfer_target_lang_key == "noline":
            output_image = gr.Image(label=lang_util.get_text("noline_image"), interactive=False, type="filepath",
                                    elem_classes=["output_image"])
        else:
            output_image = gr.Image(label=lang_util.get_text("output_image"), interactive=False, type="filepath",
                                    elem_classes=["output-image"])
            
        output_image.change(self._set_output_image, inputs=[output_image])
        clipboard_button = gr.Button("" + lang_util.get_text("clipboard"), elem_classes=["clipboard"],
                                     interactive=False)
        clipboard_button.click(self._notify, _js=javascript, queue=True)
        if self.transfer_target_lang_key is not None:
            if self.transfer_target_lang_key != "noline":
                self.transfer_button = gr.Button(lang_util.get_text(self.transfer_target_lang_key), interactive=False)
                output_image.change(lambda x: gr.update(interactive=x is not None), inputs=[output_image],
                                    outputs=[self.transfer_button])
        if self.app_config.device != "cloud" and self.app_config.device != "docker":
            if self.transfer_target_lang_key != "noline":
                gr.Button(lang_util.get_text("output_destination")).click(self._open_output_folder)

        self.output_image = output_image
        output_image.change(lambda x: gr.update(interactive=x is not None), inputs=[output_image],
                            outputs=[clipboard_button])

        return output_image

    def _set_output_image(self, output_image_path):
        self.output_image_path = output_image_path

    def _notify(self):
        if self.output_image_path is None:
            gr.Warning("Please Image Select")
        else:
            gr.Info("Image Copied to Clipboard")

    def _open_output_folder(self):
        import subprocess
        if self.app_config.device == "windows":
            subprocess.Popen(["explorer", self.app_config.output_dir])
        elif self.app_config.device == "mac":
            subprocess.Popen(["open", self.app_config.output_dir])
        else:
            subprocess.Popen(["xdg-open", self.app_config.output_dir])

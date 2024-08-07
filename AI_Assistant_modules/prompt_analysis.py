import os

import gradio as gr

from utils.prompt_utils import remove_color
from utils.tagger import modelLoad, analysis


class PromptAnalysis:
    def __init__(self, app_config, post_filter=True,
                 default_nagative_prompt="lowres, error, extra digit, fewer digits, cropped, worst quality, "
                                         "low quality, normal quality, jpeg artifacts, blurry"):
        self.default_nagative_prompt = default_nagative_prompt
        self.post_filter = post_filter
        self.model = None
        self.model_dir = os.path.join(app_config.dpath, 'models/tagger')

    def layout(self, lang_util, input_image):
        with gr.Column():
            with gr.Row():
                self.prompt_analysis_button = gr.Button(lang_util.get_text("analyze_prompt"))
            with gr.Row():
                self.prompt = gr.Textbox(label=lang_util.get_text("prompt"), lines=3)
            with gr.Row():
                self.negative_prompt = gr.Textbox(label=lang_util.get_text("negative_prompt"), lines=3, value=self.default_nagative_prompt)


        self.prompt_analysis_button.click(
            self.process_prompt_analysis,
            inputs=[input_image],
            outputs=self.prompt
        )
        return [self.prompt, self.negative_prompt]

    def process_prompt_analysis(self, input_image_path):
        if self.model is None:
            self.model = modelLoad(self.model_dir)
        tags = analysis(input_image_path, self.model_dir, self.model)
        tags_list = tags      
        if self.post_filter:
            tags_list = remove_color(tags)
        return tags_list

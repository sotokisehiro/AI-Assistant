import gradio as gr
from PIL import Image

from AI_Assistant_modules.output_image_gui import OutputImage
from AI_Assistant_modules.prompt_analysis import PromptAnalysis
from utils.img_utils import make_base_pil, base_generation, canny_process, resize_image_aspect_ratio
from utils.prompt_utils import execute_prompt, remove_color, remove_duplicates
from utils.request_api import create_and_save_images, get_lora_model

LANCZOS = (Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)


class LineDrawing:
    def __init__(self, app_config):
        self.app_config = app_config
        self.input_image = None
        self.output = None

    def layout(self, transfer_target_lang_key=None):
        lang_util = self.app_config.lang_util
        exui = self.app_config.exui        
        with gr.Row() as self.block:
            with gr.Column():
                with gr.Row():
                    with gr.Column():
                        self.input_image = gr.Image(label=lang_util.get_text("input_image"),
                                                    source="upload",
                                                    type='filepath', interactive=True)
                    with gr.Column():
                        with gr.Row():
                            canny_image = gr.Image(label=lang_util.get_text("canny_image"), type="pil",
                                                   interactive=False)
                        with gr.Row():
                            canny_threshold1 = gr.Slider(minimum=0, value=20, maximum=253, show_label=False)
                            gr.HTML(value="<span>/</span>", show_label=False)
                            canny_threshold2 = gr.Slider(minimum=0, value=120, maximum=254, show_label=False)
                            canny_generate_button = gr.Button(lang_util.get_text("generate"), interactive=False)
                if exui:
                    with gr.Row():
                        lora_model_dropdown = gr.Dropdown(label=lang_util.get_text("lora_models"), choices=[])
                        load_lora_models_button = gr.Button(lang_util.get_text("lora_update"))
                with gr.Row():
                    [prompt, nega] = PromptAnalysis(self.app_config).layout(lang_util, self.input_image)
                with gr.Row():
                    fidelity = gr.Slider(minimum=0.5, maximum=1.25, value=1.0, step=0.01, interactive=True,
                                         label=lang_util.get_text("lineart_fidelity"))
                    bold = gr.Slider(minimum=0.0, maximum=1.0, value=0.0, step=0.01, interactive=True,
                                     label=lang_util.get_text("lineart_bold"))
                with gr.Row():
                    generate_button = gr.Button(lang_util.get_text("generate"), interactive=False)
            with gr.Column():
                self.output = OutputImage(self.app_config, transfer_target_lang_key)
                output_image = self.output.layout()

        self.input_image.change(lambda x, y: gr.update(interactive=x is not None and y is not None),
                                inputs=[self.input_image, canny_image], outputs=[generate_button])
        canny_image.change(lambda x, y: gr.update(interactive=x is not None and y is not None),
                           inputs=[self.input_image, canny_image], outputs=[generate_button])
        self.input_image.change(lambda x: gr.update(interactive=x is not None), inputs=[self.input_image],
                                outputs=[canny_generate_button])

        canny_generate_button.click(self._make_canny, inputs=[self.input_image, canny_threshold1, canny_threshold2],
                                    outputs=[canny_image])

        if exui:
            load_lora_models_button.click(self.load_lora_models, inputs=[], outputs=[lora_model_dropdown])
            lora_model_dropdown.change(self.update_prompt_with_lora, inputs=[lora_model_dropdown, prompt], outputs=[prompt, lora_model_dropdown])

        generate_button.click(self._process, inputs=[
            self.input_image,
            canny_image,
            prompt,
            nega,
            fidelity,
            bold,
        ], outputs=[output_image])

    def _process(self, input_image_path, canny_image_pil, prompt_text, negative_prompt_text, fidelity, bold):
        lineart_bold = float(bold)
        lineart = 1 - lineart_bold
        prompt = "masterpiece, best quality, <lora:sdxl_BWLine:" + str(lineart) + ">, <lora:sdxl_BW_bold_Line:" + str(
            lineart_bold) + ">, monochrome, lineart, white background, " + prompt_text.strip()
        execute_tags = ["sketch", "transparent background"]
        prompt = execute_prompt(execute_tags, prompt)
        prompt = remove_duplicates(prompt)        
        prompt = remove_color(prompt)
        nega = negative_prompt_text.strip()
        base_pil = make_base_pil(input_image_path)
        base_pil = resize_image_aspect_ratio(base_pil)
        image_size = Image.open(input_image_path).size
        canny_pil = canny_image_pil.resize(base_pil.size, LANCZOS).convert("RGB")
        mask_pil = base_generation(base_pil.size, (255, 255, 255, 255)).convert("RGB")
        white_base_pil = base_generation(base_pil.size, (255, 255, 255, 255)).convert("RGB")
        image_fidelity = 1.0
        lineart_fidelity = float(fidelity)
        lineart_output_path = self.app_config.make_output_path()
        output_pil = create_and_save_images(self.app_config.fastapi_url,
                                            prompt, nega,
                                            white_base_pil, mask_pil, image_size,
                                            lineart_output_path,
                                            image_fidelity,
                                            self._make_cn_args(canny_pil, lineart_fidelity)
                                            )
        return output_pil


    def load_lora_models(self):
        model_names, model_aliases = get_lora_model(self.app_config.fastapi_url)
        model_options = [f"{name} ({alias})" for name, alias in zip(model_names, model_aliases)]
        return gr.Dropdown.update(choices=model_options, interactive=True)


    def update_prompt_with_lora(self, lora_model_selection, existing_prompt):
        if '(' in lora_model_selection and ')' in lora_model_selection:
            alias = lora_model_selection.split('(')[-1].split(')')[0].strip()
        else:
            alias = lora_model_selection

        lora_tag = f"<lora:{alias}:1.0>"
        updated_prompt = existing_prompt + ", " + lora_tag if existing_prompt else lora_tag

        #仮に『, <lora:[]:1.0>』という文字列が含まれていたら除去する
        updated_prompt = updated_prompt.replace(", <lora:[]:1.0>", "").strip()

        return updated_prompt, []
    
    def handle_lora_model_update(result):
        updated_prompt, reset_choices = result
        return gr.update(value=updated_prompt), gr.Dropdown.update(choices=reset_choices, interactive=True)


    def _make_canny(self, canny_img_path, canny_threshold1, canny_threshold2):
        threshold1 = int(canny_threshold1)
        threshold2 = int(canny_threshold2)
        return canny_process(canny_img_path, threshold1, threshold2)

    def _make_cn_args(self, canny_image_pil, lineart_fidelity):
        unit1 = {
            "image": canny_image_pil,
            "mask_image": None,
            "control_mode": "Balanced",
            "enabled": True,
            "guidance_end": 1,
            "guidance_start": 0,
            "pixel_perfect": True,
            "processor_res": 512,
            "resize_mode": "Just Resize",
            "weight": lineart_fidelity,
            "module": "None",
            "model": "control-lora-canny-rank256 [ec2dbbe4]",
            "save_detected_map": None,
            "hr_option": "Both"
        }
        unit2 = None
        return [unit1]

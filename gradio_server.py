import gradio as gr
import random
from recurrentgpt import RecurrentGPT
from human_simulator import Human
from sentence_transformers import SentenceTransformer
from utils import get_init, parse_instructions
import re

_CACHE = {}


# Build the semantic search model
embedder = SentenceTransformer('sentence-transformers/multi-qa-mpnet-base-cos-v1')

def init_prompt(novel_type, description):
    if description == "":
        description = ""
    else:
        description = " 关于 " + description
    return f"""
请按照以下精确的格式写一本{novel_type}类型的小说{description}，包含50章：

首先，写下小说的名字。
接下来，为第一章写一个大纲。大纲应描述小说的背景和开始。
根据你的大纲，写下小说的前三段。请用小说式的风格，花时间来描绘场景。
写下一段总结，捕捉到三段中的关键信息。
最后，写下三个不同的写作指示，每个包含大约五句话。每个指示应提出一个可能的、有趣的故事续写方式。
输出格式应遵循以下指南：
名称：<小说的名字>
大纲：<第一章的大纲>
第一段：<第一段的内容>
第二段：<第二段的内容>
第三段：<第三段的内容>
总结：<总结的内容>
指示 1：<写作指示1的内容>
指示 2：<写作指示2的内容>
指示 3：<写作指示3的内容>

请确保准确并严格遵守输出格式。

"""

def init(novel_type, description, request: gr.Request):
    if novel_type == "":
        novel_type = "科幻小说"
    global _CACHE
    cookie = request.headers['cookie']
    cookie = cookie.split('; _gat_gtag')[0]
    # prepare first init
    init_paragraphs = get_init(text=init_prompt(novel_type,description))
    # print(init_paragraphs)
    start_input_to_human = {
        'output_paragraph': init_paragraphs['Paragraph 3'],
        'input_paragraph': '\n\n'.join([init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']]),
        'output_memory': init_paragraphs['Summary'],
        "output_instruction": [init_paragraphs['Instruction 1'], init_paragraphs['Instruction 2'], init_paragraphs['Instruction 3']]
    }

    _CACHE[cookie] = {"start_input_to_human": start_input_to_human,
                      "init_paragraphs": init_paragraphs}
    written_paras = f"""标题： {init_paragraphs['name']}

大纲： {init_paragraphs['Outline']}

段落：

{start_input_to_human['input_paragraph']}"""
    long_memory = parse_instructions([init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']])
    # short memory, long memory, current written paragraphs, 3 next instructions
    return start_input_to_human['output_memory'], long_memory, written_paras, init_paragraphs['Instruction 1'], init_paragraphs['Instruction 2'], init_paragraphs['Instruction 3']

def step(short_memory, long_memory, instruction1, instruction2, instruction3, current_paras, request: gr.Request, ):
    if current_paras == "":
        return "", "", "", "", "", ""
    global _CACHE
    # print(list(_CACHE.keys()))
    # print(request.headers.get('cookie'))
    cookie = request.headers['cookie']
    cookie = cookie.split('; _gat_gtag')[0]
    cache = _CACHE[cookie]

    if "writer" not in cache:
        start_input_to_human = cache["start_input_to_human"]
        start_input_to_human['output_instruction'] = [
            instruction1, instruction2, instruction3]
        init_paragraphs = cache["init_paragraphs"]
        human = Human(input=start_input_to_human,
                      memory=None, embedder=embedder)
        human.step()
        start_short_memory = init_paragraphs['Summary']
        writer_start_input = human.output

        # Init writerGPT
        writer = RecurrentGPT(input=writer_start_input, short_memory=start_short_memory, long_memory=[
            init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']], memory_index=None, embedder=embedder)
        cache["writer"] = writer
        cache["human"] = human
        writer.step()
    else:
        human = cache["human"]
        writer = cache["writer"]
        output = writer.output
        output['output_memory'] = short_memory
        #randomly select one instruction out of three
        instruction_index = random.randint(0,2)
        output['output_instruction'] = [instruction1, instruction2, instruction3][instruction_index]
        human.input = output
        human.step()
        writer.input = human.output
        writer.step()

    long_memory = [[v] for v in writer.long_memory]
    # short memory, long memory, current written paragraphs, 3 next instructions
    return writer.output['output_memory'], long_memory, current_paras + '\n\n' + writer.output['input_paragraph'], human.output['output_instruction'], *writer.output['output_instruction']


def controled_step(short_memory, long_memory, selected_instruction, current_paras, request: gr.Request, ):
    if current_paras == "":
        return "", "", "", "", "", ""
    global _CACHE
    # print(list(_CACHE.keys()))
    # print(request.headers.get('cookie'))
    cookie = request.headers['cookie']
    cookie = cookie.split('; _gat_gtag')[0]
    cache = _CACHE[cookie]
    if "writer" not in cache:
        start_input_to_human = cache["start_input_to_human"]
        start_input_to_human['output_instruction'] = selected_instruction
        init_paragraphs = cache["init_paragraphs"]
        human = Human(input=start_input_to_human,
                      memory=None, embedder=embedder)
        human.step()
        start_short_memory = init_paragraphs['Summary']
        writer_start_input = human.output

        # Init writerGPT
        writer = RecurrentGPT(input=writer_start_input, short_memory=start_short_memory, long_memory=[
            init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']], memory_index=None, embedder=embedder)
        cache["writer"] = writer
        cache["human"] = human
        writer.step()
    else:
        human = cache["human"]
        writer = cache["writer"]
        output = writer.output
        output['output_memory'] = short_memory
        output['output_instruction'] = selected_instruction
        human.input = output
        human.step()
        writer.input = human.output
        writer.step()

    # short memory, long memory, current written paragraphs, 3 next instructions
    return writer.output['output_memory'], parse_instructions(writer.long_memory), current_paras + '\n\n' + writer.output['input_paragraph'], *writer.output['output_instruction']


# SelectData is a subclass of EventData
def on_select(instruction1, instruction2, instruction3, evt: gr.SelectData):
    selected_plan = int(evt.value.replace("Instruction ", ""))
    selected_plan = [instruction1, instruction2, instruction3][selected_plan-1]
    return selected_plan


with gr.Blocks(title="小说创作助手", css="footer {visibility: hidden}", theme="Base") as demo:
    gr.Markdown("# 小说创作助手")
    with gr.Tab("全自动模式"):
        with gr.Row():
            with gr.Column():
                with gr.Box():
                    with gr.Row():
                        with gr.Column(scale=1, min_width=200):
                            novel_type = gr.Textbox(
                                label="小说类型", placeholder="例如：科幻小说")
                        with gr.Column(scale=2, min_width=400):
                            description = gr.Textbox(label="描述")
                btn_init = gr.Button(
                    "初始化小说创作", variant="primary")
                gr.Examples(["玄幻","科幻","奇幻","武侠","仙侠","历史","言情","游戏","体育","灵异","同人","耽美","二次元"], inputs=[novel_type])
                written_paras = gr.Textbox(
                    label="撰写段落（可编辑）", max_lines=21, lines=21)
            with gr.Column():
                with gr.Box():
                    gr.Markdown("### 记忆模块\n")
                    short_memory = gr.Textbox(
                        label="短期记忆（可编辑）", max_lines=3, lines=3)
                    long_memory = gr.Textbox(
                        label="长期记忆（可编辑）", max_lines=6, lines=6)
                with gr.Box():
                    gr.Markdown("### 指示模块\n")
                    with gr.Row():
                        instruction1 = gr.Textbox(
                            label="指示1（可编辑）", max_lines=4, lines=4)
                        instruction2 = gr.Textbox(
                            label="指示2（可编辑）", max_lines=4, lines=4)
                        instruction3 = gr.Textbox(
                            label="指示3（可编辑）", max_lines=4, lines=4)
                    selected_plan = gr.Textbox(
                        label="修改后的指示（从最后一步开始）", max_lines=2, lines=2)

                btn_step = gr.Button("下一步", variant="primary")

        btn_init.click(init, inputs=[novel_type, description], outputs=[
            short_memory, long_memory, written_paras, instruction1, instruction2, instruction3])
        btn_step.click(step, inputs=[short_memory, long_memory, instruction1, instruction2, instruction3, written_paras], outputs=[
            short_memory, long_memory, written_paras, selected_plan, instruction1, instruction2, instruction3])

    with gr.Tab("交互式模式"):
        with gr.Row():
            with gr.Column():
                with gr.Box():
                    with gr.Row():
                        with gr.Column(scale=1, min_width=200):
                            novel_type = gr.Textbox(
                                label="小说类型", placeholder="例如：科幻小说")
                        with gr.Column(scale=2, min_width=400):
                            description = gr.Textbox(label="描述")
                btn_init = gr.Button(
                    "初始化小说创作", variant="primary")
                gr.Examples(["玄幻","科幻","奇幻","武侠","仙侠","历史","言情","游戏","体育","灵异","同人","耽美","二次元"], inputs=[novel_type])
                written_paras = gr.Textbox(
                    label="撰写段落（可编辑）", max_lines=23, lines=23)
            with gr.Column():
                with gr.Box():
                    gr.Markdown("### 记忆模块\n")
                    short_memory = gr.Textbox(
                        label="短期记忆（可编辑）", max_lines=3, lines=3)
                    long_memory = gr.Textbox(
                        label="长期记忆（可编辑）", max_lines=6, lines=6)
                with gr.Box():
                    gr.Markdown("### 指示模块\n")
                    with gr.Row():
                        instruction1 = gr.Textbox(
                            label="指示1", max_lines=3, lines=3, interactive=False)
                        instruction2 = gr.Textbox(
                            label="指示2", max_lines=3, lines=3, interactive=False)
                        instruction3 = gr.Textbox(
                            label="指示3", max_lines=3, lines=3, interactive=False)
                    with gr.Row():
                        with gr.Column(scale=1, min_width=100):
                            selected_plan = gr.Radio(["指示1", "指示2", "指示3"], label="选择指示",)
                                                    #  info="Select the instruction you want to revise and use for the next step generation.")
                        with gr.Column(scale=3, min_width=300):
                            selected_instruction = gr.Textbox(
                                label="选定的指示（可编辑）", max_lines=5, lines=5)

                btn_step = gr.Button("下一步", variant="primary")

        btn_init.click(init, inputs=[novel_type, description], outputs=[
            short_memory, long_memory, written_paras, instruction1, instruction2, instruction3])
        btn_step.click(controled_step, inputs=[short_memory, long_memory, selected_instruction, written_paras], outputs=[
            short_memory, long_memory, written_paras, instruction1, instruction2, instruction3])
        selected_plan.select(on_select, inputs=[
                             instruction1, instruction2, instruction3], outputs=[selected_instruction])

    demo.queue(concurrency_count=1)

if __name__ == "__main__":
    demo.launch(server_port=8006, share=False,
                server_name="0.0.0.0", show_api=False)

from utils import get_content_between_a_b, parse_instructions,get_api_response

class Human:

    def __init__(self, input, memory, embedder):
        self.input = input
        if memory:
            self.memory = memory
        else:
            self.memory = self.input['output_memory']
        self.embedder = embedder
        self.output = {}


    def prepare_input(self):
        previous_paragraph = self.input["input_paragraph"]
        writer_new_paragraph = self.input["output_paragraph"]
        memory = self.input["output_memory"]
        user_edited_plan = self.input["output_instruction"]

        input_text = f"""
        现在想象你是一个小说家，正在用ChatGPT写一本中文小说。你将获得一个先前写过的段落（由你写的），一个由你的ChatGPT助手写的段落，一个由你的ChatGPT助手维护的主要故事线的总结，以及一个由你的ChatGPT助手提出的下一步写什么的计划。
        我需要你写下：
        1. 扩展段落：将ChatGPT助手写的新段落扩展到你的ChatGPT助手写的段落的两倍长度。
        2. 选定计划：复制你的ChatGPT助手提出的计划。
        3. 修订计划：将选定的计划修订为下一段的大纲。

        先前写过的段落：
        {previous_paragraph}

        你的ChatGPT助手维护的主要故事线的总结：
        {memory}

        你的ChatGPT助手写的新段落：
        {writer_new_paragraph}

        你的ChatGPT助手提出的下一步写什么的计划：
        {user_edited_plan}

        现在开始写作，严格按照以下的输出格式组织你的输出，所有输出仍然保持是中文：

        扩展段落：
        <输出段落的字符串>，大约40-50个句子。

        选定计划：
        <在此处复制计划>

        修订计划：
        <修订计划的字符串>，保持简洁，大约5-7个句子。

        非常重要：
        记住你正在写一本小说。像小说家一样写作，编写下一段计划时不要过于匆忙。在选择和扩展计划时，考虑如何使计划对一般读者有吸引力。记住遵循长度限制！记住，章节将包含超过10个段落，小说将包含超过100个章节。而下一段将是第二章的第二段。你需要为未来的故事留下空间。

    """
        return input_text
    
    def parse_plan(self,response):
        plan = get_content_between_a_b('Selected Plan:','Reason',response)
        return plan


    def select_plan(self,response_file):
        
        previous_paragraph = self.input["input_paragraph"]
        writer_new_paragraph = self.input["output_paragraph"]
        memory = self.input["output_memory"]
        previous_plans = self.input["output_instruction"]
        prompt = f"""
    Now imagine you are a helpful assistant that help a novelist with decision making. You will be given a previously written paragraph and a paragraph written by a ChatGPT writing assistant, a summary of the main storyline maintained by the ChatGPT assistant, and 3 different possible plans of what to write next.
    I need you to:
    Select the most interesting and suitable plan proposed by the ChatGPT assistant.

    Previously written paragraph:  
    {previous_paragraph}

    The summary of the main storyline maintained by your ChatGPT assistant:
    {memory}

    The new paragraph written by your ChatGPT assistant:
    {writer_new_paragraph}

    Three plans of what to write next proposed by your ChatGPT assistant:
    {parse_instructions(previous_plans)}

    Now start choosing, organize your output by strictly following the output format as below:
      
    Selected Plan: 
    <copy the selected plan here>

    Reason:
    <Explain why you choose the plan>
    """
        print(prompt+'\n'+'\n')

        response = get_api_response(prompt)

        plan = self.parse_plan(response)
        while plan == None:
            response = get_api_response(prompt)
            plan= self.parse_plan(response)

        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"Selected plan here:\n{response}\n\n")

        return plan
        
    def parse_output(self, text):
        try:
            if text.splitlines()[0].startswith('Extended Paragraph'):
                new_paragraph = get_content_between_a_b(
                    'Extended Paragraph:', 'Selected Plan', text)
            else:
                new_paragraph = text.splitlines()[0]

            lines = text.splitlines()
            if lines[-1] != '\n' and lines[-1].startswith('Revised Plan:'):
                revised_plan = lines[-1][len("Revised Plan:"):]
            elif lines[-1] != '\n':
                revised_plan = lines[-1]

            output = {
                "output_paragraph": new_paragraph,
                # "selected_plan": selected_plan,
                "output_instruction": revised_plan,
                # "memory":self.input["output_memory"]
            }

            return output
        except:
            return None

    def step(self, response_file=None):

        prompt = self.prepare_input()
        print(prompt+'\n'+'\n')

        response = get_api_response(prompt)
        self.output = self.parse_output(response)
        while self.output == None:
            response = get_api_response(prompt)
            self.output = self.parse_output(response)
        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"Human's output here:\n{response}\n\n")

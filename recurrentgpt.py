from utils import get_content_between_a_b, get_api_response
import torch

import random

from sentence_transformers import  util


class RecurrentGPT:

    def __init__(self, input, short_memory, long_memory, memory_index, embedder):
        self.input = input
        self.short_memory = short_memory
        self.long_memory = long_memory
        self.embedder = embedder
        if self.long_memory and not memory_index:
            self.memory_index = self.embedder.encode(
                self.long_memory, convert_to_tensor=True)
        self.output = {}

    def prepare_input(self, new_character_prob=0.1, top_k=2):

        input_paragraph = self.input["output_paragraph"]
        input_instruction = self.input["output_instruction"]

        instruction_embedding = self.embedder.encode(
            input_instruction, convert_to_tensor=True)

        # get the top 3 most similar paragraphs from memory

        memory_scores = util.cos_sim(
            instruction_embedding, self.memory_index)[0]
        top_k_idx = torch.topk(memory_scores, k=top_k)[1]
        top_k_memory = [self.long_memory[idx] for idx in top_k_idx]
        # combine the top 3 paragraphs
        input_long_term_memory = '\n'.join(
            [f"相关段落 {i+1} :" + selected_memory for i, selected_memory in enumerate(top_k_memory)])
        # randomly decide if a new character should be introduced
        if random.random() < new_character_prob:
            new_character_prompt = f"If it is reasonable, you can introduce a new character in the output paragrah and add it into the memory."
        else:
            new_character_prompt = ""

        input_text = f"""我需要你帮我写一本小说。现在我给你一个记忆（一个简要的总结），大约400字，你应该用它来存储已经写下的关键内容，以便你能跟踪很长的上下文。每次，我会给你当前的记忆（之前故事的简要总结。你应该用它来存储已经写下的关键内容，以便你能跟踪很长的上下文），之前写下的段落，以及关于下一段要写什么的指示。
        我需要你写下：
        1. 输出段落：小说的下一段。输出段落应包含大约20个句子，并应遵循输入指示。
        2. 输出记忆：更新的记忆。你应首先解释输入记忆中哪些句子不再需要，以及为什么，然后解释需要添加什么到记忆中，以及为什么。之后你应写下更新的记忆。更新的记忆应与输入记忆相似，除了你之前认为应该删除或添加的部分。更新的记忆只应存储关键信息。更新的记忆绝不能超过20个句子！
        3. 输出指示：下一段（你写过的）要写什么的指示。你应输出3个不同的指示，每个都是故事可能的有趣延续。每个输出指示应包含大约5个句子。
        这是输入：

        输入记忆：
        {self.short_memory}

        输入段落：
        {input_paragraph}

        输入指示：
        {input_instruction}

        输入相关段落：
        {input_long_term_memory}

        现在开始写作，严格按照以下的输出格式组织你的输出：
        输出段落：
        <输出段落的字符串>，大约20个句子。

        输出记忆：
        理由：<解释如何更新记忆的字符串>；
        更新的记忆：<更新记忆的字符串>，大约10到20个句子

        输出指示：
        写作指示 1：<写作指示1的内容>，大约5个句子
        写作指示 2：<写作指示2的内容>，大约5个句子
        写作指示 3：<写作指示3的内容>，大约5个句子

        非常重要！！更新的记忆只应存储关键信息。更新的记忆中绝不能包含超过500个单词！
        最后，记住你正在写一本小说。像小说家一样写作，当编写下一段的输出指示时不要过于匆忙。记住，每个章节将包含超过10个段落，整部小说将包含超过100个章节。这只是开始。只需要写下一些接下来会发生的有趣的情节。在编写输出指示时，也要考虑哪些情节对一般读者来说是吸引人的。
        非常重要：
        你应该首先解释输入记忆中哪些句子不再必要以及为什么，然后解释需要添加什么到记忆中以及为什么。在此之后，你开始重写输入记忆以得到更新的记忆。
        {new_character_prompt}
        
    """
        return input_text

    def parse_output(self, output):
        try:
            output_paragraph = get_content_between_a_b(
                'Output Paragraph:', 'Output Memory', output)
            output_memory_updated = get_content_between_a_b(
                'Updated Memory:', 'Output Instruction:', output)
            self.short_memory = output_memory_updated
            ins_1 = get_content_between_a_b(
                'Instruction 1:', 'Instruction 2', output)
            ins_2 = get_content_between_a_b(
                'Instruction 2:', 'Instruction 3', output)
            lines = output.splitlines()
            # content of Instruction 3 may be in the same line with I3 or in the next line
            if lines[-1] != '\n' and lines[-1].startswith('Instruction 3'):
                ins_3 = lines[-1][len("Instruction 3:"):]
            elif lines[-1] != '\n':
                ins_3 = lines[-1]

            output_instructions = [ins_1, ins_2, ins_3]
            assert len(output_instructions) == 3

            output = {
                "input_paragraph": self.input["output_paragraph"],
                "output_memory": output_memory_updated,  # feed to human
                "output_paragraph": output_paragraph,
                "output_instruction": [instruction.strip() for instruction in output_instructions]
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
                f.write(f"Writer's output here:\n{response}\n\n")

        self.long_memory.append(self.input["output_paragraph"])
        self.memory_index = self.embedder.encode(
            self.long_memory, convert_to_tensor=True)

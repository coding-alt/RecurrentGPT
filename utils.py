import re
import openai

def get_api_response(content: str, max_tokens=None):

    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{
            'role': 'system',
            'content': 'You are a helpful and creative assistant for writing novel.'
        }, {
            'role': 'user',
            'content': content,
        }],
        temperature=0.5,  
        max_tokens=max_tokens
    )
    
    return response['choices'][0]['message']['content']

def get_content_between_a_b(a,b,text):
    return re.search(f"{a}(.*?)\n{b}", text, re.DOTALL).group(1).strip()


def get_init(init_text=None,text=None,response_file=None):
    """
    初始文本：如果标题、大纲和前三段内容以.txt文件的形式提供，直接进行阅读
    文本：如果没有提供.txt文件，使用初始提示来生成
    """
    if not init_text:
        response = get_api_response(text)
        print(response)

        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"初始化输出:\n{response}\n\n")
    else:
        with open(init_text,'r',encoding='utf-8') as f:
            response = f.read()
        f.close()
    paragraphs = {
        "name":"",
        "Outline":"",
        "Paragraph 1":"",
        "Paragraph 2":"",
        "Paragraph 3":"",
        "Summary": "",
        "Instruction 1":"",
        "Instruction 2":"", 
        "Instruction 3":""    
    }
    paragraphs['name'] = get_content_between_a_b('名称：','大纲：',response)
    
    paragraphs['Paragraph 1'] = get_content_between_a_b('第一段：','第二段：',response)
    paragraphs['Paragraph 2'] = get_content_between_a_b('第二段：','第三段：',response)
    paragraphs['Paragraph 3'] = get_content_between_a_b('第三段：','总结：',response)
    paragraphs['Summary'] = get_content_between_a_b('总结：','写作指示 1：',response)
    paragraphs['Instruction 1'] = get_content_between_a_b('写作指示 1：','写作指示 2：',response)
    paragraphs['Instruction 2'] = get_content_between_a_b('写作指示 2：','写作指示 3',response)
    lines = response.splitlines()
    # content of Instruction 3 may be in the same line with I3 or in the next line
    if lines[-1] != '\n' and lines[-1].startswith('写作指示 3'):
        paragraphs['Instruction 3'] = lines[-1][len("写作指示 3："):]
    elif lines[-1] != '\n':
        paragraphs['Instruction 3'] = lines[-1]
    # Sometimes it gives Chapter outline, sometimes it doesn't
    for line in lines:
        if line.startswith('章节'):
            paragraphs['Outline'] = get_content_between_a_b('大纲：','章节',response)
            break
    if paragraphs['Outline'] == '':
        paragraphs['Outline'] = get_content_between_a_b('大纲：','第一段：',response)


    return paragraphs

def get_chatgpt_response(model,prompt):
    response = ""
    for data in model.ask(prompt):
        response = data["message"]
    model.delete_conversation(model.conversation_id)
    model.reset_chat()
    return response


def parse_instructions(instructions):
    output = ""
    for i in range(len(instructions)):
        output += f"{i+1}. {instructions[i]}\n"
    return output

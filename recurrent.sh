#!/bin/bash
export OPENAI_API_KEY="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"
export OPENAI_API_BASE="https://gpt.51aiwen.com/v1"
iteration=10
outfile=response.txt
init_prompt=init_prompt.json
topic=外星人
type=科幻小说


options="\
        --iter $iteration\
        --r_file $outfile \
        --init_prompt $init_prompt \
        --topic $topic \
        --type $type \
        "
python main.py $options
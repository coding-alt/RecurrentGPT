#!/bin/bash
export OPENAI_API_KEY=""
export OPENAI_API_BASE=""
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

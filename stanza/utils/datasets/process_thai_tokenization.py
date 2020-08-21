import os
import random

from pythainlp import sent_tokenize

def write_section(output_dir, dataset_name, section, documents):
    """
    Writes a list of documents for tokenization, including a file in conll format

    The Thai datasets generally have no MWT (apparently not relevant for Thai)

    output_dir: the destination directory for the output files
    dataset_name: orchid, BEST, lst20, etc
    section: train/dev/test
    documents: a nested list of documents, paragraphs, sentences, words
      words is a list of (word, space_follows)
    """
    with open(os.path.join(output_dir, 'th_%s-ud-%s-mwt.json' % (dataset_name, section)), 'w') as fout:
        fout.write("[]\n")

    text_out = open(os.path.join(output_dir, 'th_%s.%s.txt' % (dataset_name, section)), 'w')
    label_out = open(os.path.join(output_dir, 'th_%s-ud-%s.toklabels' % (dataset_name, section)), 'w')
    for document in documents:
        for paragraph in document:
            for sentence_idx, sentence in enumerate(paragraph):
                for word_idx, word in enumerate(sentence):
                    # TODO: split with newlines to make it more readable?
                    text_out.write(word[0])
                    for i in range(len(word[0]) - 1):
                        label_out.write("0")
                    if word_idx == len(sentence) - 1:
                        label_out.write("2")
                    else:
                        label_out.write("1")
                    if word[1] and sentence_idx != len(paragraph) - 1:
                        text_out.write(' ')
                        label_out.write('0')

            text_out.write("\n\n")
            label_out.write("\n\n")

    text_out.close()
    label_out.close()

    with open(os.path.join(output_dir, 'th_%s.%s.gold.conllu' % (dataset_name, section)), 'w') as fout:
        for document in documents:
            for paragraph in document:
                for sentence in paragraph:
                    for word_idx, word in enumerate(sentence):
                        # SpaceAfter is left blank if there is space after the word
                        space = '_' if word[1] else 'SpaceAfter=No'
                        # Note the faked dependency structure: the conll reading code
                        # needs it even if it isn't being used in any way
                        fake_dep = 'root' if word_idx == 0 else 'dep'
                        fout.write('{}\t{}\t_\t_\t_\t_\t{}\t{}\t{}:{}\t{}\n'.format(word_idx+1, word[0], word_idx, fake_dep, word_idx, fake_dep, space))
                    fout.write('\n')

def write_dataset(documents, output_dir, dataset_name):
    """
    Shuffle a list of documents, write three sections
    """
    random.shuffle(documents)
    num_train = int(len(documents) * 0.8)
    num_dev = int(len(documents) * 0.1)
    os.makedirs(output_dir, exist_ok=True)
    write_section(output_dir, dataset_name, 'train', documents[:num_train])
    write_section(output_dir, dataset_name, 'dev', documents[num_train:num_train+num_dev])
    write_section(output_dir, dataset_name, 'test', documents[num_train+num_dev:])



def reprocess_lines(processed_lines):
    """
    Reprocesses lines using pythainlp to cut up sentences into shorter sentences.

    Many of the lines in BEST seem to be multiple Thai sentences concatenated, according to native Thai speakers.

    Input: a list of lines, where each line is a list of words.  Space characters can be included as words
    Output: a new list of lines, resplit using pythainlp
    """
    reprocessed_lines = []
    for line in processed_lines:
        text = "".join(line)
        chunks = sent_tokenize(text)
        # Check that the total text back is the same as the text in
        if sum(len(x) for x in chunks) != len(text):
            raise ValueError("Got unexpected text length: \n{}\nvs\n{}".format(text, chunks))

        chunk_lengths = [len(x) for x in chunks]

        current_length = 0
        new_line = []
        for word in line:
            if len(word) + current_length < chunk_lengths[0]:
                new_line.append(word)
                current_length = current_length + len(word)
            elif len(word) + current_length == chunk_lengths[0]:
                new_line.append(word)
                reprocessed_lines.append(new_line)
                new_line = []
                chunk_lengths = chunk_lengths[1:]
                current_length = 0
            else:
                remaining_len = chunk_lengths[0] - current_length
                new_line.append(word[:remaining_len])
                reprocessed_lines.append(new_line)
                word = word[remaining_len:]
                chunk_lengths = chunk_lengths[1:]
                while len(word) > chunk_lengths[0]:
                    new_line = [word[:chunk_lengths[0]]]
                    reprocessed_lines.append(new_line)
                    word = word[chunk_lengths[0]:]
                    chunk_lengths = chunk_lengths[1:]
                new_line = [word]
                current_length = len(word)
        reprocessed_lines.append(new_line)
    return reprocessed_lines

def convert_processed_lines(processed_lines):
    """
    Convert a list of sentences into documents suitable for the output methods in this module.

    Input: a list of lines, including space words
    Output: a list of documents, each document containing a list of sentences
            Each sentence is a list of words: (text, space_follows)
            Space words will be eliminated.
    """
    paragraphs = []
    sentences = []
    for words in processed_lines:
        # turn the words into a sentence
        sentence = []
        for word in words:
            word = word.strip()
            if not word:
                if len(sentence) == 0:
                    raise ValueError("Unexpected space at start of sentence in document {}".format(filename))
                sentence[-1] = (sentence[-1][0], True)
            else:
                sentence.append((word, False))
        # blank lines are very rare in best, but why not treat them as a paragraph break
        if len(sentence) == 0:
            paragraphs.append([sentences])
            sentences = []
            continue
        sentence[-1] = (sentence[-1][0], True)
        sentences.append(sentence)
    paragraphs.append([sentences])
    return paragraphs


import os

from nltk import word_tokenize, tokenize as nltk_tokenize, pos_tag, chunk
from nltk.corpus import wordnet
from nltk.tag import StanfordPOSTagger
import nltk
from spacy import displacy


# en_nlp, de_nlp = setup_nlp()
# this_dir = os.path.dirname(os.path.abspath(__file__))

# TODO: this is very slow, it might work out better to start this seperately and use a local api:
# start in background
# nohup java -mx1000m -cp nlp/stanford-postagger-full-2020-11-17/stanford-postagger.jar edu.stanford.nlp.tagger.maxent.MaxentTaggerServer -model nlp/stanford-postagger-full-2020-11-17/models/german-ud.tagger -port 2020 >& /dev/null &

# adjust firewall:
# iptables -A INPUT -p tcp -s localhost --dport 2020 -j ACCEPT
# iptables -A INPUT -p tcp --dport 2020 -j DROP
# tagger = StanfordPOSTagger(
#     model_filename=this_dir + '/stanford-postagger-full-2020-11-17/models/german-ud.tagger',
#     path_to_jar=this_dir + '/stanford-postagger-full-2020-11-17/stanford-postagger-4.2.0.jar'
# )

# TODO: welche Library sollte man hier am besten verwenden?
#   Liegt der Fokus der Arbeit auf dem Vergleich von Algorithmen?
#   ============
#   https://spacy.io/usage/facts-figures#comparison-usage
#   ============
#   spaCy is built on the latest research, but it’s not a research library. If your goal is to write papers and run
#   benchmarks, spaCy is probably not a good choice. However, you can use it to make the results of your research easily
#   available for others to use, e.g. via a custom spaCy component.


# def tokenize(string):
    # a = nltk_tokenize(string)
    # a = 1
    # options = {"compact": True, "bg": "#09a3d5", "color": "white", "font": "Source Sans Pro"}
    # string = 'Es existiert ein Benutzer. Wenn er eine Anfrage gegen die Endroute /abc macht, dann ' \
    #          'sollte dies funktionieren. Account.'
    # doc = de_nlp(string)
    # displacy.serve(doc, style="dep")
    # b = tagger.tag(word_tokenize(string, language='german'))
    # tree = chunk.ne_chunk(b)
    # return de_nlp(string)

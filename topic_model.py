import pandas as pd
import numpy as np
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import RegexpTokenizer
from nltk.stem.wordnet import WordNetLemmatizer
from gensim.corpora import Dictionary
from gensim.models import LdaModel

class TopicModel:

    def __init__(self):
        return

    def prepare_data(self, data):
        
        # Group the data by the letter id and concatenate words from each letter to one string
        strings = data.groupby(['ID', 'Sender']).agg(lambda col: ' '.join(col))

        # Create a list of strings of the letters for Gensim
        docs = list(strings['Words'])
        
        # Split the documents into tokens.
        tokenizer = RegexpTokenizer(r'\w+')
        
        for idx in range(len(docs)):
            docs[idx] = docs[idx].lower()  # Convert to lowercase.
            docs[idx] = tokenizer.tokenize(docs[idx])  # Split into words.

        # Remove numbers, but not words that contain numbers.
        docs = [[token for token in doc if not token.isnumeric()] for doc in docs]

        # Remove words that are only one character.
        docs = [[token for token in doc if len(token) > 1] for doc in docs]
        
        # Lemmatize the documents.
        lemmatizer = WordNetLemmatizer()
        docs = [[lemmatizer.lemmatize(token) for token in doc] for doc in docs]
        
        # Create a dictionary representation of the documents.
        dictionary = Dictionary(docs)

        # Filter out words that occur less than 10 documents, or more than 50% of the documents.
        #dictionary.filter_extremes(no_below=10, no_above=0.5)
        
        # Bag-of-words representation of the documents.
        corpus = [dictionary.doc2bow(doc) for doc in docs]
        
        return corpus, dictionary, docs, strings

    # Filter the data based on the POS tags 
    def filter_by_tag(self, data, tags):
        tag_data = data.loc[data['Tags'].isin(tags)]
        
        return tag_data

    # Filter the data based on the gender of the author
    def filter_by_sex(self, data, sex):
        gender_data = data.loc[data['SenderSex'] == sex]
        
        return gender_data

    # Filter the data based on the rank of the author
    def filter_by_rank(self, data, rank):
        rank_data = data.loc[data['SenderRank'].isin(rank)]
        
        return rank_data
    
    # Filter the data based on the relationship between the author and the recipient
    def filter_by_rel(self, data, rel):
        rel_data = data.loc[data['RelCode'].isin(rel)]
        
        return rel_data
    
    # Filter the data based on the selected period
    def filter_by_time(self, data, time):
        period_data = data.loc[(data["Year"] >= time[0]) & (data["Year"] <= time[1])]

        return period_data

    # Train the LDA topic model
    def train_lda(self, data, dictionary, n_topics, n_iter):
        
        # Set training parameters.
        num_topics = n_topics
        chunksize = 1000
        passes = 1
        iterations = n_iter
        eval_every = None  
        # Set random seed
        random_seed = 135
        state = np.random.RandomState(random_seed)


        # Train LDA model.
        model = LdaModel(
            corpus=data,
            id2word=dictionary,
            chunksize=chunksize,
            alpha='auto',
            eta='auto',
            iterations=iterations,
            num_topics=num_topics,
            passes=passes,
            eval_every=eval_every,
            random_state=state
        )
        
        top_topics = model.top_topics(data)
        
        return model, top_topics

    # Lists the main topics for each letter
    def letter_topics(self, ldamodel, corpus, texts):
        # Init output
        topics_df = pd.DataFrame()

        # Get main topic in each letter
        for i, row in enumerate(ldamodel[corpus]):
            row = sorted(row, key=lambda x: (x[1]), reverse=True)
            # Get the dominant topic, percentage contribution and keywords for each letter
            for j, (topic_num, prop_topic) in enumerate(row):
                if j == 0:  # dominant topic
                    wp = ldamodel.show_topic(topic_num)
                    topic_keywords = ", ".join([word for word, prop in wp])
                    topics_df = topics_df.append(pd.Series([int(topic_num), round(prop_topic,4), topic_keywords]), ignore_index=True)
                else:
                    break
        topics_df.columns = ['Dominant topic', 'Contribution of topic to letter', 'Topic keywords']

        # Add letter and sender id to the end of the output dataframe
        senders = texts.index.to_frame(index=False)
        topics_df = pd.concat([topics_df, senders], axis=1)

        return topics_df

    # Lists for each topic a letter where the topic had the largest contribution
    def get_most_representative(self, dominant_topics):

        topics_sorted = pd.DataFrame()

        topics_out = dominant_topics.groupby('Dominant topic')

        for i, grp in topics_out:
            topics_sorted = pd.concat([topics_sorted, grp.sort_values(['Contribution of topic to letter'], ascending=[0]).head(1)],axis=0)

        # Reset Index    
        topics_sorted.reset_index(drop=True, inplace=True)

        # Format
        topics_sorted.columns = ['Topic', "Contribution of topic to letter", "Topic keywords", "Letter id", "Sender"]

        topics_sorted["Contribution of topic to letter"] = topics_sorted["Contribution of topic to letter"].round(decimals=3)

        return topics_sorted

    # Counts the number and percentage of documents for which each topic is dominant
    def letters_per_topic(self, dominant_topics):

        # Number of documents for each topic
        topic_counts = dominant_topics['Dominant topic'].value_counts()

        # Number of senders for each topic
        sender_counts = dominant_topics.groupby('Dominant topic')["Sender"].nunique()

        topics_senders = pd.concat([pd.Series(topic_counts),pd.Series(sender_counts)], axis=1).reindex(topic_counts.index)

        # Percentage of documents for each topic
        topic_contribution = round(topic_counts/topic_counts.sum(), 4)

        # Topic number and keywords
        topic_num_keywords = dominant_topics[['Dominant topic', 'Topic keywords']].drop_duplicates().set_index('Dominant topic', drop=False)

        # Concatenate columnwise
        df_docs = pd.concat([topic_num_keywords, topics_senders, topic_contribution], axis=1)

        # Change column names
        df_docs.columns = ['Dominant topic', 'Topic keywords', 'Number of selected letters', 'Number of senders', 'Proportion of selected letters']
        
        df_docs.reset_index(drop=True, inplace=True)

        return df_docs
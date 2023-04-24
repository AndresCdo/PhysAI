import numpy as np
from tensorflow.keras.layers import LSTM, Dense, Embedding
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer


class LaTeXModel:
    def __init__(self, latex_data, epochs=50, batch_size=64):
        self.latex_data = latex_data
        self.epochs = epochs
        self.batch_size = batch_size
        self.tokenizer = Tokenizer(char_level=True)
        self.tokenizer.fit_on_texts(latex_data)
        self.vocab_size = len(self.tokenizer.word_index) + 1
        self.max_length = None
        self.input_sequences, self.output_sequences = self.prepare_sequences()
        self.model = self.build_model()

    def prepare_sequences(self):
        sequences = self.tokenizer.texts_to_sequences(self.latex_data)
        input_sequences, output_sequences = [], []

        for sequence in sequences:
            for i in range(1, len(sequence)):
                input_sequences.append(sequence[:i])
                output_sequences.append(sequence[i])

        max_length = max([len(seq) for seq in input_sequences])
        self.max_length = max_length
        input_sequences = pad_sequences(
            input_sequences, maxlen=max_length, padding="pre"
        )
        output_sequences = np.array(output_sequences)

        return input_sequences, output_sequences

    def build_model(self):
        model = Sequential(
            [
                Embedding(self.vocab_size, 128, input_length=self.max_length),
                LSTM(256),
                Dense(self.vocab_size, activation="softmax"),
            ]
        )
        model.compile(
            loss="sparse_categorical_crossentropy",
            optimizer=Adam(),
            metrics=["accuracy"],
        )

        return model

    def train(self):
        self.model.fit(
            self.input_sequences,
            self.output_sequences,
            epochs=self.epochs,
            batch_size=self.batch_size,
        )

import json
import random
import shutil

import spacy
from spacy.training.example import Example
from spacy.util import minibatch


class NerController:
    def __init__(self, model_path, language=None, labels=None, data_path=None, learn_rate=None, iterations=None,
                 batch_size=None, data_list=None):
        self.labels = labels
        self.language = language
        self.model_path = model_path
        self.data_path = data_path
        self.learn_rate = learn_rate
        self.iterations = iterations
        self.batch_size = batch_size
        self.train_data = data_list

        # Cargar datos desde el archivo JSON si existe
        if data_path and os.path.exists(data_path):  # Verifica si el archivo existe
            try:
                with open(data_path, 'r', encoding='utf-8') as file:
                    self.train_data = json.load(file)
                print(f"Datos cargados correctamente desde {data_path}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error al cargar el archivo JSON: {e}")
        elif data_list:
            print("Usando datos de entrenamiento proporcionados directamente.")
        else:
            print("Advertencia: No se proporcionaron datos de entrenamiento.")

    def create_ner_model(self):
        # Load the language model
        nlp = spacy.blank(self.language)

        # Add ner component
        if "ner" not in nlp.pipe_names:
            ner = nlp.add_pipe("ner")
        else:
            ner = nlp.get_pipe("ner")

        # Add labels to the ner component
        for label in self.labels:
            ner.add_label(label)

        # Train the model
        training_results = self.data_trainer(ner, nlp)

        # Save the model
        nlp.to_disk(self.model_path)
        print("The new data model has been created")
        return training_results

    # Method for deleting the ner data model
    def delete_ner_model(self):
        shutil.rmtree(self.model_path)

    # Method for training model
    def train_ner_model(self):
        try:
            nlp = spacy.load(self.model_path);
            print('model loaded successfully')
        except OSError as e:
            print(f'Error loading NER model: {e}')

        # Add ner to pipeline if not present
        if 'ner' not in nlp.pipe_names:
            ner = nlp.add_pipe("ner")
        else:
            ner = nlp.get_pipe("ner")

        # Train model
        training_results = self.data_trainer(ner, nlp)

        # Save the model
        nlp.to_disk(self.model_path)
        print("The data model has been trained")
        return training_results

    # Method for analyzing data
    def analyze_data(self):
        # Load the trained model
        nlp = spacy.load(self.model_path)

        # Analyze the data with the trained model and return the results
        results = []
        for index, data in enumerate(self.train_data):
            text = data["text"]
            doc = nlp(text.strip())
            entities = []
            if doc.ents:
                for ent in doc.ents:
                    entities.append([ent.start_char, ent.end_char, ent.label_, ent.text])
                    print(ent.text, ent.label_)
            results.append({"index": index, "text": data["text"], "entities": entities})

        return results

    # Method for training the model with the given data
    def data_trainer(self, ner, model):
        # Training configuration
        optimizer = model.initialize()
        optimizer.learn_rate = self.learn_rate

        #List for holding result data
        results = []

        for epoch in range(self.iterations):
            random.shuffle(self.train_data)
            losses = {}
            # Create example from the data
            # Update the model with the example in batches
            for batch in minibatch(self.train_data, size=self.batch_size):
                # List to store examples
                examples = []

                # Create examples from the current batch of data
                for item in batch:
                    text = item["text"]
                    annotations = {"entities": [[start, end, label] for start, end, label, _ in
                                                item["entities"]]}  # Eliminamos el texto extraído
                    examples.append(Example.from_dict(model.make_doc(text), annotations))

                # Update the model with the examples in the current batch
                ner.update(examples, drop=0.5, losses=losses, sgd=optimizer)
            total_loss = sum(losses.values()) / len(losses) if losses else 0
            results.append({'iteration': epoch, 'losses': float(total_loss)})
            print(f"Losses at epoch {epoch}: {losses}")

        print(results)
        # Return result list
        return results
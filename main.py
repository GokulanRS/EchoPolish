from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
import azure.cognitiveservices.speech as speechsdk
from gramformer import Gramformer
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import threading

class SpeechRecognitionApp(App):
    def _init_(self):
        super()._init_()
        self.recognized_list = []
        self.corrected_list = []
        self.input_output_pairs = []
        self.stop_recognition = False
        self.recognition_thread = None
        self.grammar_model = None

    def build(self):
        layout = BoxLayout(orientation='vertical', spacing=10)

        # Set application title
        self.title = "EchoPolish"

        # Set background color of the window to white
        Window.clearcolor = (1, 1, 1, 1)

        # Add label for the app name and logo in a horizontal layout
        header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=100)
        
        # Add the logo to the header layout
        logo_image = Image(source=r"C:\Users\Gokul\Desktop\Gokulan\Logo.jpeg", size_hint=(0.2, 1))
        header_layout.add_widget(logo_image)

        # Add the title label to the header layout
        app_name_label = Label(text="EchoPolish", font_size=64, color=(0, 0, 0, 1), size_hint=(0.8, 1), halign='center', valign='middle')
        header_layout.add_widget(app_name_label)

        layout.add_widget(header_layout)

        # ScrollView for the output label
        scroll_view = ScrollView(do_scroll_y=True)
        self.output_label = Label(text="", font_size=16, color=(0, 0, 0, 1), halign='center', valign='top', text_size=(None, None))
        self.output_label.bind(size=self.output_label.setter('text_size'))
        scroll_view.add_widget(self.output_label)
        layout.add_widget(scroll_view)

        # Horizontal layout for buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)

        # Button to start recognition
        self.start_recognition_button = Button(text="Start Recognition", font_size=32,
                                          background_color=(0, 1, 0, 1))
        self.start_recognition_button.bind(on_press=self.start_recognition)
        button_layout.add_widget(self.start_recognition_button)

        # Button to stop recognition
        self.stop_recognition_button = Button(text="Stop Recognition", font_size=32,
                                         background_color=(1, 0, 0, 1))
        self.stop_recognition_button.bind(on_press=self.stop_recognition_callback)
        button_layout.add_widget(self.stop_recognition_button)

        layout.add_widget(button_layout)

        return layout

    def on_start(self):
        # Load grammar model when the app starts
        self.load_grammar_model()

    def start_recognition(self, instance):
        print("Speech recognition started...")
        self.recognized_list = []
        self.corrected_list = []
        self.input_output_pairs = []
        self.stop_recognition = False

        self.recognition_thread = threading.Thread(target=self.run_recognition)
        self.recognition_thread.start()

    def update_output_label(self, recognized_text, corrected_text):
        # Update the output label with recognized and corrected text
        if corrected_text == {recognized_text}:
            self.output_label.text += "Spoken by You: {}\n".format(recognized_text)
            self.output_label.text += "No correction needed\n"
        else:
            self.output_label.text += "Spoken by You: {}\n".format(recognized_text)
            self.output_label.text += "Corrected Sentence: {}\n".format(corrected_text)
        self.output_label.text += "--------------------------------------------------------------------------------------------------------------------------------------------\n"
        self.output_label.height = self.output_label.texture_size[1]  # Adjust height based on the content

    def run_recognition(self):
        speech_config = speechsdk.SpeechConfig(subscription="1ade45cc3dc64abeb5a19e9d381bb2df", region="westus")  
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

        while not self.stop_recognition:
            result = speech_recognizer.recognize_once()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text
                self.recognized_list.append(recognized_text)
                corrected_text = self.grammar_model.correct(recognized_text)
                self.corrected_list.append(corrected_text)
                self.input_output_pairs.append((recognized_text, corrected_text))
                Clock.schedule_once(lambda dt: self.update_output_label(recognized_text, corrected_text))
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("No speech could be recognized: {}".format(result.no_match_details))
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print("Speech Recognition canceled: {}".format(cancellation_details.reason))
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print("Error details: {}".format(cancellation_details.error_details))
            if self.stop_recognition:
                break

    def stop_recognition_callback(self, instance):
        print("Speech recognition stopped.")
        self.stop_recognition = True
        if self.recognition_thread:
            self.recognition_thread.join()
        # Generate PDF after recognition process is finished
        output_path = "output.pdf"
        self.create_pdf(output_path)

    def load_grammar_model(self):
        print("Loading grammar correction model...")
        self.grammar_model = Gramformer(models=1, use_gpu=False)
        print("Grammar correction model loaded.")

    def build_pdf_content(self):
        output_content = []
        output_content.append("Speech Recognition and Grammar Check Results")
        output_content.append("--------------------------------------------------------------------------------------------------------------------------------------------")

        for recognized_text, corrected_text in self.input_output_pairs:
            output_content.append(f"Spoken by You: {recognized_text}")
            if corrected_text == {recognized_text}:
                output_content.append("No correction needed")
            else:
                output_content.append(f"Corrected Sentence: {corrected_text}")
            output_content.append("--------------------------------------------------------------------------------------------------------------------------------------------")
        
        return output_content

    def create_pdf(self, output_path):
        output_content = self.build_pdf_content()

        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 16)
        title = "EchoPolish"
        title_width = c.stringWidth(title, "Helvetica-Bold", 16)
        title_x = (width - title_width) / 2  # Calculate x-coordinate for center alignment
        c.drawString(title_x, height - 40, title)

        c.setFont("Helvetica", 12)
        y_position = height - 80
        for line in output_content:
            if y_position < 40:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 40
            c.drawCentredString(width / 2, y_position, line)  # Center align the text
            y_position -= 20

        c.save()

if __name__ == '__main__':
    SpeechRecognitionApp().run()


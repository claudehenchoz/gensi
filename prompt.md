Generate a Python application that processes .gensi files as documented in 'gensi-format-specification.md'.

The Python app should be both usable as a GUI app (which should be the default handler for .gensi files) and as a CLI app.

* Use PySide6 to implement the GUI
  * The GUI should show a progress bar, indicating which items are being downloaded, show the cover as the rest of the content is retrieved, then once done, it should stay in the list
  * The GUI should look similar to the 'Transmission' GUI client - except for .torrent files and bittorrent, it uses the .gensi files and web downloads for generating the epubs
* Use click to implement the CLI
* Make sure that both use the same logic for the actual processing of .gensi files into .epub files
* Use curl_cffi with chrome136 impersonation for all web retrieval
* Use lxml for processing the retrieved html (incl. handling of the css selectors)
* Use any relevant and modern library to implement parallel processing/multithreading (do up to 5 retrievals in parallel), but ensure they work across both GUI and CLI
* Use nh3 to sanitize the retrieved articles so they only contain the tags supported by the EPUB 2.0.1 standard
* Use any relevant and modern library to ensure that the snippets conform to xhtml standards required EPUB 2.0.1
* Use jinja2 and a template to apply a uniform article layout and style across all epubs
* Make the code very well-structured and easy to maintain/extend
* Make the code and README use 'uv' to manage the project

Also: Create a todo list to keep track of your progress

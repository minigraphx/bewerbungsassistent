# Dialog

Bestätigung vor einer Handlung mit Folgen, als natives `<dialog>`; ersetzt das Muster „Knopf wechselt den Text, nochmals klicken“.

**Der Verwender liefert:** `<dialog class="dialog">` geöffnet mit `showModal()`, Titel als Frage in `dialog__title` („Anschreiben ersetzen?“), ein Satz mit der Folge und wo die alte Fassung bleibt in `dialog__text`, zwei Knöpfe in `dialog__actions`: Abbrechen zuerst und mit `autofocus`, die Handlung als Verb rechts.

**Hauptknopf oder Gefahr:** Lässt sich die Handlung zurückholen (Ersetzen, Erfassen), ist sie `btn--primary`. Nur Unumkehrbares (Entwurf endgültig löschen, App beenden während eines Laufs) ist `btn--danger`.

**Auch für:** Doppelbewerbung („Bei Muster AG läuft schon eine Bewerbung. Trotzdem öffnen?“), Versand erfassen, Datei überschreiben, App beenden.

**Nicht:** Dialoge für reine Information (dafür `Notice`); „Ja“ und „Nein“ als Knopftext.

import email, smtplib, ssl
from email.mime.text import MIMEText
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

import requests


class envoi:
    def __init__(
        self,
        nom_fichLog,
        affich,
        fichConf,
        charg,
        validRecu,
        validDump,
        validPasPareil,
        validCompression,
        validConn,
        validUpload,
    ):
        self.nom_fichLog = nom_fichLog
        self.affich = affich
        self.iniconf = fichConf
        self.charg = charg
        self.validRecu = validRecu
        self.validDump = validDump
        self.validPasPareil = validPasPareil
        self.validCompression = validCompression
        self.validConn = validConn
        self.validUpload = validUpload

    def notif_mattermost(self):

        try:
            headers = {
                "Content-Type": "application/json",
            }
            values = (
                '{  "text":"#### Resultat du script  : '
                + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                + "\n"
            )
            values += " | Etapes                 | Etats                                   |\n"
            values += " |:-----------            |:-----------------------------------------|\n"
            values += (
                " | Chargement du fichier de config          | "
                + self.charg
                + "                       |\n"
)
            values += (
                " | Telechargement du fichier          | "
                +  self.validRecu
                + "                       |\n"
            )
            values += (
                " | Dump SQL present         | "
                + self.validDump
                + "                       |\n"
            )
            values += (
                " | Comparaison des fichiers        | "
                + self.validPasPareil
                + "                       |\n"
            )
            values += (
                " | Compression du fichier          | "
                + self.validCompression
                + "                       |\n"
            )
            values += (
                " | Connexion au serveur SMB         | "
                + self.validConn
                + "                       |\n"
            )
            values += (
                " | Fichier recu sur le serveur        | "
                + self.validUpload
                + "                       |\n"
            )
            values += '"}'
            requests.post(str(self.iniconf["mattermost"]["webhook"]),
            headers=headers,
            data=values,
            )
            self.affich.info("Notification mattermost envoyée")
        except requests.exceptions.RequestException as e:
            self.affich.error("Problème lors de l'envoi de la notification mattermost" + str(e))
        finally:
            self.affich.info("|||| Notification mattermost terminée ||||")
    
    def envoi_email(self):
        try:
            email_source = self.iniconf["mail"]["email_source"]
            email_destination = self.iniconf["mail"]["email_destination"]
            mdp = self.iniconf["mail"]["mdp"]

            message = MIMEMultipart("alternative")
            message["Subject"] = "Resultat du script le : " + str(datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
            message["From"] = email_source
            message["To"] = email_destination

            if self.charg == ":no_entry:":
                chargement = "&#10060;"
            else:
                chargement = "&#9989;"

            if self.validRecu == ":no_entry:":
                telechargement = "&#10060;"
            else:
                telechargement = "&#9989;"

            if self.validDump == ":no_entry:":
                presence_dump = "&#10060;"
            else:
                presence_dump = "&#9989;"

            if self.validPasPareil == ":no_entry:":
                similaire = "&#10060;"
            else:
                if self.validPasPareil == ":warning:":
                    similaire = "&#9888;"
                else:
                    similaire = "&#9989;"

            if self.validCompression == ":no_entry:":
                compression = "&#10060;"
            else:
                compression = "&#9989;"

            if self.validConn == ":no_entry:":
                connexion_serv = "&#10060;"
            else:
                connexion_serv = "&#9989;"
            if self.validUpload == ":no_entry:":
                envoi_serv = "&#10060;"
            else:
                envoi_serv = "&#9989;"

            html = (
                """\
            <html>
            <head>
            <meta charset='utf-8'>
            </head>
            <body>
            """
                + """<p> <br> Chargement du fichier conf : """
                + chargement
                + """<br> Téléchargement du fichier zip : 
                """
                + telechargement
                + """<br> Présence du dump SQL : 
                """
                + presence_dump
                + """ <br> Comparaison : 
                """
                + similaire
                + """ <br> Compression : 
                """
                + compression
                + """ <br> Connexion au serveur SMB : 
                """
                + connexion_serv
                + """ <br> Envoi du fichier au serveur : 
                """
                + envoi_serv
                + """
            </body>
            </html>
            """
            )

            mail = MIMEText(html, "html")
            message.attach(mail)
            log = self.nom_fichLog
            with open(log, "rb") as attachment:
                fich_joint = MIMEBase("application", "octet-stream")
                fich_joint.set_payload(attachment.read())
            encoders.encode_base64(fich_joint)
            fich_joint.add_header("Content-Disposition",f"attachment; filename= {log}",)
            message.attach(fich_joint)

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(email_source, mdp)
                server.sendmail(email_source, email_destination, message.as_string())
            self.affich.info("Email envoyé")
        except (email.errors.MessageError, smtplib.SMTPException) as e:
            self.affich.error("Email non envoyé" + str(e))
        finally:
            self.affich.info("|||| Partie Email terminée ||||")
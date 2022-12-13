from smb.SMBHandler import SMBHandler
from datetime import datetime
from shutil import copyfileobj
from smb.SMBConnection import *
from urllib.request import urlopen

import tempfile
import urllib
import logging
import configparser
import inform
import zipfile
import requests
import datetime as dateT
import os, time
import tarfile


class script:

    def __init__(self, fichLog, fichConf):

        self.affich = logging.getLogger(__name__)
        self.affich.setLevel(logging.INFO)
        fileHandler = logging.FileHandler(fichLog)
        fileHandler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s  %(name)s  %(levelname)s: %(message)s")
        fileHandler.setFormatter(formatter)
        self.affich.addHandler(fileHandler)
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.INFO)
        self.affich.addHandler(consoleHandler)
        self.charg = ":no_entry:"
        self.validRecu = ":no_entry:"
        self.validDump = ":no_entry:"
        self.validPasPareil = ":no_entry:"
        self.validCompression = ":no_entry:"
        self.validConn = ":no_entry:"
        self.validUpload = ":no_entry:"
        self.nom_fichLog = fichLog

        try:
            self.iniconf = configparser.ConfigParser()
            self.conf_file_name = str(fichConf)
            self.iniconf.read(self.conf_file_name)
            self.affich.info(" - Lecture du fichier config - ")
            self.affich.info("####  Vérification de la présence des différentes sections ####")
            if (
                self.iniconf.has_section("url_fichier_zip")
                and self.iniconf.has_section("smb")
                and self.iniconf.has_section("historisation")
                and self.iniconf.has_section("mail")
                and self.iniconf.has_section("mattermost")
            ):
                self.affich.info("Toutes les sections ont bien été détectées")
                self.validConfig = True
            else:
                self.affich.error(" !!! Erreur : Il manque une ou plusieurs sections au fichier config !!!")
                self.validConfig = False
                raise configparser.Error
            while self.validConfig:
                self.affich.info(
                    "####  Vérification de la présence des différentes options des sections ####"
                )
                if self.iniconf.has_option("url_fichier_zip", "url"):
                    self.affich.info("Le lien vers le fichier zip est bien présent")
                else:
                    self.affich.error(" !!! Erreur : Le lien vers le fichier zip est absent !!!")
                    self.validConfig = False
                    raise configparser.Error
                if (
                    self.iniconf.has_option("smb", "user")
                    and self.iniconf.has_option("smb", "mdp")
                    and self.iniconf.has_option("smb", "adresse_ip")
                    and self.iniconf.has_option("smb", "dossier_partage")
                    and self.iniconf.has_option("smb", "nom_pc_local")
                    and self.iniconf.has_option("smb", "nom_pc_serveur")
                    and self.iniconf.has_option("smb", "port")
                ):
                    self.affich.info("Les paramètres de la section SMB sont complets")
                else:
                    self.affich.error(" !!! Erreur : Les paramètres de la section SMB sont incomplets !!!")
                    self.validConfig = False
                    raise configparser.Error
                if  self.iniconf.has_option("historisation", "nbrJours"):
                    self.affich.info("L'historisation est bien paramétrée")
                else:
                    self.affich.error("!!! Erreur : L'historisation est mal paramétrée !!!")
                    self.validConfig = False
                    raise configparser.Error
                if  (
                    self.iniconf.has_option("mail", "email_source") 
                    and self.iniconf.has_option("mail", "mdp")
                    and self.iniconf.has_option("mail", "email_destination")
                ):
                    self.affich.info("Les options du mail sont remplies")
                else:
                    self.affich.error("!!! Erreur : Les options du mail ne sont pas remplies !!!")
                    self.validConfig = False
                    raise configparser.Error
                if self.iniconf.has_option("mattermost", "webhook"):
                    self.affich.info("Le webhook de mattermost est présent")
                    self.charg = ":white_check_mark:"
                    break
                else:
                    self.affich.error(" !!! Erreur : Le webhook de mattermost est absent !!!")
                    self.validConfig = False
                    raise configparser.Error
            self.affich.info("Le fichier config a été chargé avec succès")
        except configparser.Error as e:
            self.affich.error("Problème lors du chargement du fichier confing.ini" + str(e))
        finally:
            self.affich.info("|||| Initialisation terminée ||||")

    def zip_recup(self):

        try:
            self.affich.info(" - Téléchargement du zip -")
            url = self.iniconf["url_fichier_zip"]["url"]
            if not os.path.exists("./Recu"):
                try:
                    os.makedirs("./Recu")
                except OSError as exc:
                    self.affich.error("Problème" + str(exc))
            with urlopen(url) as in_stream, open('./Recu/retrieved.zip', 'wb') as res:
                copyfileobj(in_stream, res)
            self.affich.info("Téléchargement terminé")
            self.validRecu = ":white_check_mark:"
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as e:
            self.affich.error("Problème lors du téléchargement " + str(e))
        finally:
            self.affich.info("|||| Téléchargement terminé ||||")

    def extraction_comparaison(self):
        try:
            self.affich.info("####  Comparaison puis extraction en cours ####")
            zip = zipfile.ZipFile("./Recu/retrieved.zip", "r", zipfile.ZIP_DEFLATED)
            if "test_export.sql" in zip.namelist():
                self.validDump = ":white_check_mark:"
                self.affich.info("Présence du dump sql vérifié")
                if self.iniconf["premiere_fois"]["oui_ou_non"] == "oui":
                    self.validPasPareil = ":warning:"
                    self.affich.warning("Ceci est la première fois que vous lancer le script donc pas de comparaison pour le fichier test_export.sql.")
                    self.affich.warning("Merci de ne pas supprimer le fichier test_export.sql (il servira pour les comparaisons future")
                    self.iniconf.set("premiere_fois", "oui_ou_non", "non")
                    config = open(self.conf_file_name, "w")
                    self.iniconf.write(config)
                    date_zip = datetime(*zip.getinfo("test_export.sql").date_time)
                    zip.extract("test_export.sql", path="./Recu/", pwd=None)
                    moduloTime = time.mktime(date_zip.timetuple())
                    os.utime("./Recu/test_export.sql", (moduloTime, moduloTime))
                else:
                    date_zip = datetime(*zip.getinfo("test_export.sql").date_time)
                    print(
                        "Le fichier sql extrait du zip date du %s"
                        % date_zip.strftime("%Y - %m - %d , %H:%M")
                    )
                    verifDate = datetime.fromtimestamp(
                        os.path.getmtime("./Recu/test_export.sql")
                    )
                    print(
                        "Le fichier de référence date du %s"
                        % verifDate.strftime("%Y - %m - %d , %H:%M")
                    )
                    self.affich.info("On compare le nouveau : %s avec l'ancien : %s" % (date_zip.strftime("%Y - %m - %d , %H:%M"),verifDate.strftime("%Y - %m - %d , %H:%M"),))
                    date_zip_temp = date_zip.strftime("%Y - %m - %d , %H:%M")
                    file_date = verifDate.strftime("%Y - %m - %d , %H:%M")
                    if (datetime.strptime(date_zip_temp, "%Y - %m - %d , %H:%M") == datetime.strptime(file_date, "%Y - %m - %d , %H:%M") or 
                        datetime.strptime(date_zip_temp, "%Y - %m - %d , %H:%M") < datetime.strptime(file_date, "%Y - %m - %d , %H:%M")):
                        self.affich.warning("Le nouveau fichier n'est pas plus récent")
                        raise Exception("Le nouveau fichier n'est pas plus récent")
                    else:
                        self.validPasPareil = ":white_check_mark:"
                        self.affich.info("Les fichiers sont différents, préparation à l'envoi (de-zip)")
                        os.remove("./Recu/test_export.sql")
                        zip.extract("test_export.sql", path="./Recu/", pwd=None)
                        moduloTime = time.mktime(date_zip.timetuple())
                        os.utime("./Recu/test_export.sql", (moduloTime, moduloTime))
            else:
                self.affich.error("Le fichier SQL n'a pas été trouvé dans le zip")
        except (OSError, Exception) as e:
            self.affich.error(
                "Problème lors de l'extraction : " + str(e)
            )
        finally:
            self.affich.info(
                "|||| Extraction terminée ||||"
            )
            zip.close()
            os.remove("./Recu/retrieved.zip")

    def compression(self):
        try:
            self.affich.info("- Compression démarrée -")
            filename = datetime.now().strftime("%Y%d%m")
            tf = tarfile.open(filename + ".tar.gz", mode="w:gz")
            tf.add("./Recu/test_export.sql", arcname="test_export.sql")
            tf.close()
            self.validCompression = ":white_check_mark:"
        except (OSError, tarfile.TarError) as e:
            self.affich.error("Probleme durant la compression :" + str(e))
        finally:
            self.affich.info("|||| Compression terminée ||||")
            tf.close()

    def envoi_smb(self):
        self.affich.info("- Envoi au serveur SMB -")
        
        conn = SMBConnection(self.iniconf["smb"]["user"], self.iniconf["smb"]["mdp"],self.iniconf["smb"]["nom_pc_local"], self.iniconf["smb"]["nom_pc_serveur"], use_ntlm_v2 = True)
        conn.connect(self.iniconf["smb"]["adresse_ip"], self.iniconf["smb"]["port"])

        self.affich.info("Connecté à "  + str(self.iniconf["smb"]["adresse_ip"]) + " en tant que " + str(self.iniconf["smb"]["user"]))
        
        files = conn.listPath(self.iniconf["smb"]["dossier_partage"], "/") 
        
        self.affich.info("Liste des fichiers sur le serveur :")
        for item in files:
            if item.filename != '.' and item.filename != '..':
                self.affich.info(item.filename)

        self.validConn = ":white_check_mark:"
        if self.iniconf["historisation"]["actif"] == "oui":
                        self.affich.info("L'historisation est définie comme active ... Vérification")
                        date_min = ( dateT.datetime.now() - dateT.timedelta(int(self.iniconf["historisation"]["nbrJours"]))).strftime("%Y%d%m")
                        for item in files:
                            if item.filename != '.' and item.filename != '..':
                                self.affich.info("Vérification de la date de " + item.filename)
                                if datetime.strptime(item.filename[0:8], "%Y%d%m") < datetime.strptime(date_min, "%Y%d%m"):
                                    self.affich.info("Suppression du fichier datant de plus longtemps que "+ self.iniconf["historisation"]["nbrJours"]+ " jours")
                                    conn.deleteFiles(self.iniconf["smb"]["dossier_partage"], item.filename, delete_matching_folders=False)
                                else:
                                    self.affich.info("Le fichier est encore valable")
        else:
            self.affich.info("L'historisation est désactivée pas de contrôle des fichiers distants")
        fichier = datetime.now().strftime("%Y%d%m") + ".tar.gz"
        self.affich.info("Envoi du fichier " + fichier + " au serveur")
        with open(fichier, "rb") as file_obj:
            conn.storeFile(self.iniconf["smb"]["dossier_partage"], "/"+fichier, file_obj)
        file_obj.close()
        self.validUpload = ":white_check_mark:"
        self.affich.info("|||| L'envoi au serveur SMB est terminé ||||")
        os.remove(fichier)



def main():
    verif_script = script("recap.log", "config.ini")
    if verif_script.validConfig == True:
        verif_script.zip_recup()
        if verif_script.validRecu == ":white_check_mark:":
            verif_script.extraction_comparaison()
            if verif_script.validDump == ":white_check_mark:" and (
                verif_script.validPasPareil == ":white_check_mark:"
                or verif_script.validPasPareil == ":warning:"
            ):
                verif_script.compression()
                if verif_script.validCompression == ":white_check_mark:":
                    verif_script.envoi_smb()
                    if verif_script.validUpload == ":white_check_mark:":
                        verif_script.affich.info("Le script s'est executé correctement.")
                    else:
                        verif_script.affich.error(
                            "Le script s'est arrêté lors de l'envoi SMB"
                        )
                else:
                    verif_script.affich.error(
                        "Le script s'est arrêté lors de la compression"
                    )
            else:
                verif_script.affich.error(
                    "Le script s'est arrêté lors de la comparaison et extraction"
                )
        else:
            verif_script.affich.error(
                "Le script s'est arrêté lors du telechargement du fichier zip "
            )
    else:
        verif_script.affich.error(
            "Le script s'est arrêté lors de l'initialisation "
        )
    informe = inform.envoi(
        verif_script.nom_fichLog,
        verif_script.affich,
        verif_script.iniconf,
        verif_script.charg,
        verif_script.validRecu,
        verif_script.validDump,
        verif_script.validPasPareil,
        verif_script.validCompression,
        verif_script.validConn,
        verif_script.validUpload,
    )
    informe.notif_mattermost()
    informe.envoi_email()


if __name__ == "__main__":
    main()

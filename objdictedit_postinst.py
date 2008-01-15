#!/usr/bin/env python
# -*- coding: utf-8 -*-

# La premi�re ligne doit commencer par #! et contenir python.
# Elle sera adapt�e au syst�me de destination automatiquement

""" This is a part of Beremiz project.

    Post installation script for win32 system
    
    This script creat a shortcut for objdictedit.py in the desktop and the
    start menu, and remove them at the uninstallation
    
"""

import os
import sys

# Ce script sera aussi lanc� lors de la d�sinstallation.
# Pour n'ex�cuter du code que lors de l'installation :
if sys.argv[1] == '-install':
    # On r�cup�re le dossier o� mes fichiers seront install�s (dossier o� python est aussi install� sous windows)
    python_path = sys.prefix
    # On r�cup�re le chemin de pythonw.exe (l'ex�cutable python qui n'affiche pas de console).
    # Si vous voulez une console, remplacez pythonw.exe par python.exe
    pyw_path = os.path.abspath(os.path.join(python_path, 'pythonw.exe'))
    # On r�cup�re le dossier coincoin
    objdictedit_dir = os.path.abspath(os.path.join(python_path, 'LOLITech', 'CanFestival-3','objdictgen'))
    ############################################################################
    #objdictedit_dir = os.path.abspath(os.path.join(python_path, 'share', \
                                                    #'objdictedit'))
    ############################################################################
    # On r�cup�re les chemins de coincoin.py, et de coincoin.ico
    # (Ben oui, l'icone est au format ico, oubliez le svg, ici on en est encore � la pr�histoire.
    # Heureusement que the GIMP sait faire la conversion !)
    ico_path = os.path.join(objdictedit_dir, 'objdictedit.ico')
    script_path = os.path.join(objdictedit_dir, 'objdictedit.py')
    
    # Cr�ation des raccourcis
    # Pour chaque raccourci, on essaye de le faire pour tous les utilisateurs (Windows NT/2000/XP),
    # sinon on le fait pour l'utilisateur courant (Windows 95/98/ME)
    
    # Raccourcis du bureau
    # On essaye de trouver un bureau
    try:
        desktop_path = get_special_folder_path("CSIDL_COMMON_DESKTOPDIRECTORY")
    except OSError:
        desktop_path = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
    
    # On cr�� le raccourcis
    create_shortcut(pyw_path, # programme � lancer
                    "Can Node Editor", # Description
                    os.path.join(desktop_path, 'objdictedit.lnk'),  # fichier du raccourcis (gardez le .lnk)
                    script_path, # Argument (script python)
                    objdictedit_dir, # Dossier courant
                    ico_path # Fichier de l'icone
                    )
    # On va cafter au programme de d�sinstallation qu'on a fait un fichier, pour qu'il soit supprim�
    # lors de la d�sinstallation
    file_created(os.path.join(desktop_path, 'objdictedit.lnk'))
    
    # Raccourcis dans le menu d�marrer (idem qu'avant)
    try:
        start_path = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
    except OSError:
        start_path = get_special_folder_path("CSIDL_PROGRAMS")
    
    

    # Cr�ation du dossier dans le menu programme
    programs_path = os.path.join(start_path, "LOLITech")
    try :
        os.mkdir(programs_path)

    except OSError:

        pass
    directory_created(programs_path)
    
    create_shortcut(pyw_path, # Cible
                    "Can Node Editor", #Description
                    os.path.join(programs_path, 'objdictedit.lnk'),  # Fichier
                    script_path, # Argument
                    objdictedit_dir, # Dossier de travail
                    ico_path # Icone
                    )
    file_created(os.path.join(programs_path, 'objdictedit.lnk'))
    
    # End (youpi-message)
    # Ce message sera affich� (tr�s) furtivement dans l'installateur.
    # Vous pouvez vous en servir comme moyen de communication secret, c'est tr�s in.
    sys.stdout.write("Shortcuts created.")
    # Fin du bidule
    sys.exit()

# -*- coding: utf-8 -*-

import logging
import subprocess
import re

"""
Prompts for aeios
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.0"
__all__ = ['Button', 'Prompt', 'Cancelled', 'confirm', 'ignore', 'automation']

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

# NOTES: It might be advantageous to have adapter.Prompt here, but not now


class Error(Exception):
    pass


class Cancelled(Error):
    """
    Raised when user cancels
    """
    pass


class Button(object):
    """
    Class to attach functions to buttons
    """
    @staticmethod
    def _callback(result):
        logger = logging.getLogger(__name__)
        logger.debug("creating default callback: returning %r", result)

        def _wrapped():
            return result

        logger.debug("returning wrapper function")
        return _wrapped
        
    def __init__(self, text, callback=None, default=False):
        self.log = logging.getLogger(__name__ + '.Button')
        _msg = "initializing Button({0!r}, {1!r}, {2!r})"
        self.log.debug(_msg.format(text, callback, default))
        self.text = text
        self.callback = callback if callback else self._callback(text)
        self.default = default
    
    def __str__(self):
        try:
            return self.text.encode('utf-8')
        except UnicodeDecodeError:
            return self.text
    
    def __unicode__(self):
        try:
            return self.text.decode('utf-8')
        except UnicodeEncodeError:
            return self.text

    def __repr__(self):
        return u"Button({0.text!r}, {1.callback!r})".format(self, self)
    
    def press(self):
        self.log.debug(u"pressing '%s'", self)
        return self.callback()

       
class Prompt(object):

    def __init__(self, msg, details=None, buttons=()):
        self.log = logging.getLogger(__name__ + '.Prompt')
        self.msg = msg
        self.details = details
        if not buttons:
            # buttons = (Button("OK"), Cancel())
            buttons = (Button("OK"), Button("Cancel"))
        self.buttons = buttons
    
    def display(self):
        """
        Build AppleScript dialog and 
        """
        self.log.debug("displaying prompt")
        scpt = u'display alert "{0!s}"'.format(self.msg)
        if self.details:
            self.log.debug("adding details: %s", self.details)
            scpt += u' message "{0!s}"'.format(self.details)
        
        # Button("OK"), Button("Cancel") -> r'{"OK", "Cancel"}'
        b_str = '", "'.join([str(x) for x in self.buttons])
        scpt += u' as critical buttons {{"{0!s}"}}'.format(b_str)

        # get all default buttons
        default = [b for b in self.buttons if b.default]
        if default:
            self.log.debug("adding default button: %s", default[0])
            # use first default encountered
            scpt += u' default button "{0!s}"'.format(default[0])

        # execute the AppleScript
        self.log.debug("> osascript -e %r", scpt)
        #out = subprocess.check_output(['osascript', '-e', scpt]).rstrip()
        out = subprocess.check_output(['osascript', '-e', scpt])
        self.log.debug("output: %r", out)

        result = re.match(r'^button returned:(.+)$', out).group(1)
        button = [b for b in self.buttons if b.text == result][0]

        if button.text == 'Cancel':
            # cancel out of this prompt (stops recursion)
            raise Cancelled("prompt was cancelled")
        else:
            try:
                return button.press()
            except Cancelled:
                # re-display this prompt if another prompt was opened
                self.log.debug("re-displaying prompt")
                return self.display()


def confirm(device):
    """
    Displays Erase Confirmation message
    """
    logger = logging.getLogger(__name__)
    logger.debug("started: %s", device)
        
    message = u"Are you sure you want to erase “{0!s}”?".format(device)
    details = ('This device will be automatically erased each time it'
               ' is connected to this system.\n\n'
               'This cannot be undone.')
    buttons = (Button("Cancel"), Button("Erase"))

    prompt = Prompt(message, details, buttons)

    def _button_callback():
        logger.debug("running callback")
        return prompt.display()

    return _button_callback


def ignore(device):
    """
    Displays Ignore Confirmation message
    """
    logger = logging.getLogger(__name__)
    logger.debug("started: %s", device)

    message = u"Exclude “{0!s}” from automation?".format(device)
    details = "You will no longer be prompted when this device is connected."
    buttons = (Button("Ignore"), Button("Cancel"))

    prompt = Prompt(message, details, buttons)

    def _button_callback():
        logger.debug("running callback")
        return prompt.display()

    return _button_callback
    

def automation(device):
    """
    Main Dialog Window that prompts for Automation:
        Ignore -> Confirm
        Automatically Erase -> 
    """
    message = (u"aeiOS wants to automatically Erase “{0!s}”.").format(device)
    details = ("This device will be automatically erased each time it"
               " is connected to this system.")
    buttons = (Button("Ignore Device", ignore(device)),
               Button("Automatically Erase", confirm(device)),
               Button("Cancel"))

    return Prompt(message, details, buttons).display()
        

if __name__ == '__main__':
    pass

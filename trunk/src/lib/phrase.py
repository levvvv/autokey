
# Copyright (C) 2008 Chris Dekter

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import re
from configurationmanager import *

DEFAULT_WORDCHAR_REGEX = '[\w]'

def get_first_item_by_key(dictionary):
    keys = dictionary.keys()
    keys.sort()
    return dictionary[keys[0]]

def get_next_item_by_key(dictionary, currentKey):
    try:
        keys = dictionary.keys()
        keys.sort()
        index = keys.index(currentKey)        
        key = keys[index + 1]
        return dictionary[key]
    except IndexError:
        return None
    
def get_item_index(dictionary, key):
    keys = dictionary.keys()
    keys.sort()
    return keys.index(key)
    
def get_nth_item_by_key(index, dictionary1, dictionary2={}):
    totalItems = len(dictionary1) + len(dictionary2)
    if index >= (totalItems):
        return None
    else:
        if index >= len(dictionary1):
            # Index is in second dictionary
            index -= len(dictionary1)
            return __getNthItem(index, dictionary2)
        else:
            return __getNthItem(index, dictionary1)
            
def __getNthItem(index, dictionary):
    keys = dictionary.keys()
    keys.sort()
    return dictionary[keys[index]]    

class AbstractAbbreviation:
    """
    Abstract class encapsulating the common functionality of an abbreviation
    """

    def __init__(self):
        self.abbreviation = None
        self.backspace = True
        self.ignoreCase = False
        self.immediate = False
        self.triggerInside = False
        self.wordChars = re.compile(DEFAULT_WORDCHAR_REGEX, re.UNICODE)
                        
    def set_word_chars(self, regex):
        self.wordChars = re.compile(regex, re.UNICODE)
        
    def get_word_chars(self):
        return self.wordChars.pattern
        
    def set_abbreviation(self, abbr):
        self.abbreviation = abbr
        
    def _should_trigger_abbreviation(self, buffer):
        """
        Checks whether, based on the settings for the abbreviation and the given input,
        the abbreviation should trigger.
        
        @param buffer Input buffer to be checked (as string)
        """
        stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
        
        if len(typedAbbr) > 0:            
            # Check trigger character condition
            if not self.immediate:
                # If not immediate expansion, check last character
                if len(stringAfter) == 1:
                    # Have a character after abbr
                    if self.wordChars.match(stringAfter):
                        # last character(s) is a word char, can't send expansion
                        return False
                    elif len(stringAfter) > 1:
                        # Abbr not at/near end of buffer any more, can't send
                        return False
                else:
                    # Nothing after abbr yet, can't expand yet
                    return False
            
            else:
                # immediate option enabled, check abbr is at end of buffer
                if len(stringAfter) > 0:
                    return False
                
            # Check chars ahead of abbr
            # length of stringBefore should always be > 0
            if len(stringBefore) > 0:
                if self.wordChars.match(stringBefore[-1]):
                    # last char before is a word char
                    if not self.triggerInside:
                        # can't trigger when inside a word
                        return False
            
            return True
        
        return False
    
    def _partition_input(self, currentString):
        """
        Partition the input into text before, text after, and typed abbreviation (if it exists)
        """
        if self.ignoreCase:
            matchString = currentString.lower()
            stringBefore, typedAbbr, stringAfter = matchString.rpartition(self.abbreviation)
            abbrStart = len(stringBefore)
            abbrEnd = abbrStart + len(typedAbbr)
            typedAbbr = currentString[abbrStart:abbrEnd]
        else:
            stringBefore, typedAbbr, stringAfter = currentString.rpartition(self.abbreviation)     
            
        return (stringBefore, typedAbbr, stringAfter)
    
            
class AbstractWindowFilter:
    
    def __init__(self):
        self.windowTitleRegex = None
    
    def set_window_titles(self, regex):
        if regex is not None:
            self.windowTitleRegex = re.compile(regex, re.UNICODE)
        else:
            self.windowTitleRegex = regex
            
    def uses_default_filter(self):
        return self.windowTitleRegex is None
    
    def get_filter_regex(self):
        if self.windowTitleRegex is not None:
            return self.windowTitleRegex.pattern
        else:
            return ""

    def _should_trigger_window_title(self, windowTitle):
        if self.windowTitleRegex is not None:
            return self.windowTitleRegex.match(windowTitle)
        else:
            return True        
            
            
class AbstractHotkey(AbstractWindowFilter):
    
    def __init__(self):
        self.modifiers = []
        self.hotKey = None
        
    def set_hotkey(self, modifiers, key):
        modifiers.sort()
        self.modifiers = modifiers
        self.hotKey = key
        
    def check_hotkey(self, modifiers, key, windowTitle):
        if self.hotKey is not None and self._should_trigger_window_title(windowTitle):
            return (self.modifiers == modifiers) and (self.hotKey == key)
        else:
            return False
    
        
class PhraseFolder(AbstractAbbreviation, AbstractHotkey, AbstractWindowFilter):
    """
    Manages a collection of phrases, which may be associated with an abbreviation or hotkey.
    """
    
    def __init__(self, title, showInTrayMenu=False):
        AbstractAbbreviation.__init__(self)
        AbstractHotkey.__init__(self)
        AbstractWindowFilter.__init__(self)
        self.title = title
        self.folders = {}
        self.phrases = {}
        self.modes = set()
        self.usageCount = 0
        self.showInTrayMenu = showInTrayMenu
        self.parent = None
        
    def get_tuple(self):
        return ("folder", self.title, "", self)
    
    def set_modes(self, modes):
        self.modes = modes
        
    def add_folder(self, folder):
        folder.parent = self
        self.folders[folder.title] = folder
        
    def remove_folder(self, folder):
        del self.folders[folder.title]
        
    def add_phrase(self, phrase):
        """
        Add a new phrase to the folder.
        """
        phrase.parent = self
        self.phrases[phrase.description] = phrase
        
    def remove_phrase(self, phrase):
        """
        Removes the given phrase from the folder.
        """
        del self.phrases[phrase.description]
        
    def set_modes(self, modes):
        self.modes = modes
        
    def check_input(self, buffer, windowName):
        if PhraseMode.ABBREVIATION in self.modes:
            return self._should_trigger_abbreviation(buffer) and self._should_trigger_window_title(windowName)
        else:
            return False
        
    def increment_usage_count(self):
        self.usageCount += 1
        if self.parent is not None:
            self.parent.increment_usage_count()
        
    def get_backspace_count(self, buffer):
        """
        Given the input buffer, calculate how many backspaces are needed to erase the text
        that triggered this folder.
        """
        if PhraseMode.ABBREVIATION in self.modes and self.backspace:
            if self._should_trigger_abbreviation(buffer):
                stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
                return len(self.abbreviation) + len(stringAfter)
        
        if self.parent is not None:
            return self.parent.get_backspace_count(buffer)

        return 0
        
    # Tree model utility methods ----
        
    def get_child(self, childRef):
        """
        Return the child object (folder or phrase) for the given child reference.
        """
        if childRef in self.folders.keys():
            return self.folders[childRef]
        else:
            return self.phrases[childRef]
        
    def get_next_child(self, child):
        childRef = str(child)
        if childRef in self.folders.keys():
            # Child is a folder
            nextChild = get_next_item_by_key(self.folders, childRef)
            if nextChild is not None:
                return nextChild
            else:
                return get_first_item_by_key(self.phrases)
        else:
            return get_next_item_by_key(self.phrases, childRef)
        
    def has_children(self):
        return self.get_child_count() > 0
    
    def get_child_count(self):
        return len(self.folders) + len(self.phrases)
    
    def get_first_child(self):
        if len(self.folders) > 0:
            return get_first_item_by_key(self.folders)
        elif len(self.phrases) > 0:
            return get_first_item_by_key(self.phrases)
        else:
            return None
        
    def get_nth_child(self, index):
        return get_nth_item_by_key(index, self.folders, self.phrases)
    
    def get_child_index(self, child):
        if isinstance(child, PhraseFolder):
            return get_item_index(self.folders, str(child))
        else:
            return get_item_index(self.phrases, str(child)) + len(self.folders)
        
    def __cmp__(self, other):
        if self.usageCount != other.usageCount:
            return cmp(self.usageCount, other.usageCount)
        else:
            return cmp(other.title, self.title)
    
    def __str__(self):
        return self.title
    
    def __repr__(self):
        return str(self)


class PhraseMode:
    """
    Enumeration class for phrase match modes.
    
    NONE: Don't trigger this phrase (phrase will only be shown in its folder).
    ABBREVIATION: Trigger this phrase using an abbreviation.
    PREDICTIVE: Trigger this phrase using predictive mode.
    """
    NONE = 0
    ABBREVIATION = 1
    PREDICTIVE = 2
    HOTKEY = 3


class Phrase(AbstractAbbreviation, AbstractHotkey, AbstractWindowFilter):
    """
    Encapsulates all data and behaviour for a phrase.
    """
    
    def __init__(self, description, phrase):
        AbstractAbbreviation.__init__(self)
        AbstractHotkey.__init__(self)
        AbstractWindowFilter.__init__(self)
        self.description = description
        self.phrase = phrase
        self.modes = []
        self.usageCount = 0
        self.prompt = False
        self.omitTrigger = False
        self.matchCase = False
        self.parent = None
        self.showInTrayMenu = False

    def get_tuple(self):
        return ("gtk-paste", self.description, self.abbreviation, self)
        
    def set_modes(self, modes):
        self.modes = modes

    def check_input(self, buffer, windowName):
        if self._should_trigger_window_title(windowName):
            abbr = False
            predict = False
            
            if PhraseMode.ABBREVIATION in self.modes:
                abbr = self._should_trigger_abbreviation(buffer)
            if PhraseMode.PREDICTIVE in self.modes:
                predict = self._should_trigger_predictive(buffer)
            
            return (abbr or predict)
            
        return False
    
    def build_phrase(self, buffer):
        self.usageCount += 1
        self.parent.increment_usage_count()
        expansion = Expansion(self.phrase)
        triggerFound = False
        
        if PhraseMode.ABBREVIATION in self.modes:
            if self._should_trigger_abbreviation(buffer):
                stringBefore, typedAbbr, stringAfter = self._partition_input(buffer)
                triggerFound = True        
                if self.backspace:
                    # determine how many backspaces to send
                    expansion.backspaces = len(self.abbreviation) + len(stringAfter)
                
                if not self.omitTrigger:
                    expansion.string += stringAfter
                    
                if self.matchCase:
                    if typedAbbr.istitle():
                        expansion.string = expansion.string.title()
                    elif typedAbbr.isupper():
                        expansion.string = expansion.string.upper()
                    elif typedAbbr.islower():
                        expansion.string = expansion.string.lower()
                        
        if PhraseMode.PREDICTIVE in self.modes:
            if self._should_trigger_predictive(buffer):
                expansion.string = expansion.string[ConfigurationManager.predictiveLength:]
                triggerFound = True
            
        if not triggerFound:
            # Phrase could have been triggered from menu - check parents for backspace count
            expansion.backspaces = self.parent.get_backspace_count(buffer)
        
        self.__parsePositionTokens(expansion)
        return expansion
    
    def _should_trigger_predictive(self, buffer):
        if len(buffer) >= ConfigurationManager.predictiveLength: 
            typed = buffer[-ConfigurationManager.predictiveLength:]
            return self.phrase.startswith(typed)
        else:
            return False
        
    def __parsePositionTokens(self, expansion):
        # Check the string for cursor positioning token and apply lefts and ups as appropriate
        if '%%' in expansion.string:
            firstpart, secondpart = expansion.string.split('%%')
            expansion.string = firstpart + secondpart
            expansion.lefts = len(secondpart)
        
    def __cmp__(self, other):
        if self.usageCount != other.usageCount:
            return cmp(self.usageCount, other.usageCount)
        else:
            return cmp(other.description, self.description)

    
    def __str__(self):
        return self.description
    
    def __repr__(self):
        return "Phrase('" + self.description + "')"

class Expansion:
    
    def __init__(self, string):
        self.string = string
        self.lefts = 0
        self.backspaces = 0
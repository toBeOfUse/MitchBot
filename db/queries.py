"""
Allows Python code to access the word frequency and wiktionary words databases (which
are in SQLite and bespoke trie database forms, respectively.)
"""

import sqlite3
import struct
from typing import Optional
from io import BytesIO
import traceback
from timeit import default_timer as timer
import cython
import trieparse

words_db = sqlite3.connect("db/words.db")


def get_word_frequency(word: str) -> int:
    """
    Exposes the word frequency data stored in words.db to easy python access.
    """
    cur = words_db.cursor()
    frequency = cur.execute(
        "select frequency from words where word=?",
        (word,)
    ).fetchone()
    return 0 if frequency is None else frequency[0]


class TrieNode():
    """
    Stores a node in a trie that supports latin characters a-z (sorry, more
    interesting alphabets.) Contains recursive functions for adding strings to itself
    and serializing itself to bytes (which can be used for v fast searches in the C
    side of this amalgamation. Searching through pure Python TrieNodes, as the Trie
    class does, is also very fast, but it takes a while to create all the required
    TrieNode objects from a large dataset like all-wiktionary0english-words.txt.)
    """
    num_nodes = 0
    header_format = "?i"
    link_format = "cL"
    _bytes_written = 0

    def __init__(self):
        self.links: list[Optional[TrieNode]] = [None]*26
        self.completes_word = False
        self._byte_offset = -1
        TrieNode.num_nodes += 1

    def add_string(self, new_string: str) -> None:
        if len(new_string) == 0:
            self.completes_word = True
            return
        assert new_string[0] in "abcdefghijklmnopqrstuvwxyz"
        next_char = ord(new_string[0])-ord("a")
        if self.links[next_char] is not None:
            self.links[next_char].add_string(new_string[1:])
        else:
            new_node = TrieNode()
            self.links[next_char] = new_node
            new_node.add_string(new_string[1:])

    def to_bytes(self, buffer: BytesIO) -> int:
        """Adds itself and the nodes to which it links to the provided buffer and
        returns the byte offset of the structure storing itself within the provided
        buffer. Nodes are stored in the following format: one boolean value
        corresponding to self.completes_word, one int describing how many other nodes
        this node links to, and then that many char-long pairs storing a lowercase
        ascii character and the byte offset that the corresponding node is stored at.
        In Python struct format string format: '?i(cL...)'"""
        if self._byte_offset != -1:
            return self._byte_offset
        else:
            byte_offset = TrieNode._bytes_written
            buffer.seek(byte_offset)
            valid_links = [(c, n) for c, n in enumerate(
                self.links, start=ord('a')) if n is not None]
            TrieNode._bytes_written += buffer.write(struct.pack(
                self.header_format, self.completes_word, len(valid_links)))
            # reserve space for the cL pairs. we can find out what the offsets of the
            # child nodes are after they are written to the buffer, but in the
            # meantime we must reserve space for ourself, with 0s
            for _ in valid_links:
                TrieNode._bytes_written += buffer.write(
                    struct.pack(self.link_format, '\0'.encode("ascii"), 0))
            self._byte_offset = byte_offset
            link_offsets = [(chr(c), n.to_bytes(buffer)) for c, n in valid_links]
            old_pos = buffer.tell()
            buffer.seek(byte_offset+struct.calcsize(self.header_format))
            for character, node_pos in link_offsets:
                buffer.write(struct.pack(self.link_format, character.encode("ascii"), node_pos))
            buffer.seek(old_pos)

            return byte_offset

    @classmethod
    def from_bytes(cls, buffer: bytes, byte_offset: int = 0) -> "TrieNode":
        """deserializes the TrieNode located at a specific byte offset in the buffer.
        by default, the root node of the serialized trie is targeted."""
        new_node = cls()
        new_node.completes_word, link_count = struct.unpack_from(
            cls.header_format, buffer, byte_offset)
        read_bytes = struct.calcsize(cls.header_format)
        for i in range(link_count):
            character, node_offset = struct.unpack_from(
                cls.link_format, buffer, byte_offset+read_bytes)
            read_bytes += struct.calcsize(cls.link_format)
            new_node.links[ord(character.decode("ascii"))-ord('a')
                           ] = cls.from_bytes(buffer, node_offset)
        return new_node


class Trie():
    """
    Wraps either a TrieNode that's the root of a trie or a buffer of serialized
    TrieNodes and provides functions to add strings to them (TrieNode mode only for
    now) and search through them. Searching through buffer-based data, which is
    really fast to load compared to creating TrieNodes from either raw data, pickles,
    or binary data, is done with the trieparse.c Cython extension; the Python version
    of the search was really slow, trust me.
    """

    def __init__(self, root: TrieNode = None, buffer: bytes = None):
        if buffer is not None:
            self.buffer = buffer
            self.mode = "bytes"
        elif root is not None:
            self.root = root
            self.mode = "objects"
        else:
            self.root = TrieNode()
            self.mode = "objects"

    def add_string(self, new_string: str):
        if self.mode == "objects":
            self.root.add_string(new_string)
        else:
            raise NotImplementedError("add_string not supported for Tries based on bytes")

    def to_bytes(self) -> bytes:
        if self.mode == "bytes":
            return self.buffer
        else:
            buffer = BytesIO()
            self.root.to_bytes(buffer)
            buffer.seek(0)
            self.root._bytes_written = 0
            return buffer.read()

    def search_words_by_letters(self, eligible_characters: list[str]) -> set[str]:
        """
        Search for strings in the Trie that contain only the passed-in eligible
        characters.
        """
        if self.mode == "objects":
            result = set()

            def search_node(node: TrieNode, word_so_far: str):
                if node.completes_word:
                    result.add(word_so_far)
                for letter in eligible_characters:
                    letter_code = ord(letter)-ord("a")
                    if node.links[letter_code] is not None:
                        search_node(node.links[letter_code], word_so_far+letter)

            search_node(self.root, "")
            return result
        else:
            raw_result: bytes = trieparse.search(
                self.buffer, "".join(eligible_characters).encode("ascii"))
            result = set(raw_result.decode("ascii").split())
            return result


_wiktionary_trie_cached = None


def get_wiktionary_trie() -> Trie:
    """
    Returns a searchable Trie of all of the English words in Wiktionary (data from
    https://github.com/tatuylonen/wiktextract). The trie is created from either the
    raw data or a stored binary version of the final data structure the first time
    this is called, and then returned from cache thereafter.
    """
    global _wiktionary_trie_cached
    if _wiktionary_trie_cached is None:
        wiktionary_words_bytes_path = "db/wiktionary-trie.bin"
        try:
            with open(wiktionary_words_bytes_path, "rb") as wwb:
                print("reading wiktionary word trie from saved bytes")
                wiktionary_words = Trie(buffer=wwb.read())
        except:
            print("could not load wiktionary word trie from bytes; " +
                  "reconstituting it (may take a few seconds)")
            traceback.print_exc()
            wiktionary_words = Trie()
            with open("db/all-wiktionary-english-words.txt", encoding="utf-8") as wiktionary_file:
                for line in wiktionary_file:
                    word = line.strip()
                    eligible = True
                    for character in word:
                        if character not in "abcdefghijklmnopqrstuvwxyz":
                            eligible = False
                    if eligible and len(word) > 0:
                        wiktionary_words.add_string(word)
            # serialize Trie so that the next run can use the quick-load buffer version
            serialized_words = wiktionary_words.to_bytes()
            with open(wiktionary_words_bytes_path, "wb") as wwb:
                wwb.write(serialized_words)
            print("done;", TrieNode.num_nodes, "trie nodes created")
        _wiktionary_trie_cached = wiktionary_words
    return _wiktionary_trie_cached


if __name__ == "__main__":
    test_trie = get_wiktionary_trie()
    print("searching trie for words with specific letters")
    start = timer()
    print(test_trie.search_words_by_letters(list("filchng")))
    print("took", round((timer()-start)*1000, 2), "ms")

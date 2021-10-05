#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct TrieHeader {
    unsigned char completes_word;
    int num_links;
} _header;

struct TrieLink {
    char letter;
    long byte_offset;
} _link;

void searchTrie(char* base, long offset, char word_so_far[32],
    int word_so_far_length, char* results, int* results_length,
    char* eligible_indexes)
{
    const struct TrieHeader* current = (struct TrieHeader*)(base + offset);
    if (current->completes_word && word_so_far_length > 3) {
        strcpy(results + *results_length, word_so_far);
        *results_length += strlen(word_so_far);
        results[*results_length] = ' ';
        results[(*results_length) + 1] = '\0';
        *results_length += 2;
    }
    struct TrieLink* first_link = (struct TrieLink*)(current + 1);
    for (int i = 0; i < current->num_links; i++) {
        struct TrieLink* link = first_link + i;
        for (int i = 0; i < 7; i++) {
            if (eligible_indexes[i] == link->letter) {
                char new_word_so_far[32];
                strcpy(new_word_so_far, word_so_far);
                new_word_so_far[word_so_far_length] = link->letter;
                new_word_so_far[word_so_far_length + 1] = 0;
                searchTrie(base, link->byte_offset, new_word_so_far,
                    word_so_far_length + 1, results, eligible_indexes,
                    results_length);
            }
        }
    }
}

const char* search_words(const char* eligibleCharacters)
{
    FILE* trie_file = fopen("db/wiktionary-trie.bin", "rb");

    fseek(trie_file, 0L, SEEK_END);
    long sz = ftell(trie_file);
    rewind(trie_file);

    char* nodes = malloc(sz);
    size_t result = fread((void*)nodes, 1, sz, trie_file);
    fclose(trie_file);

    char* results = malloc(10000);
    char word_so_far[32];
    word_so_far[0] = 0;
    int resultsLength = 0;
    searchTrie(
        nodes, 0, word_so_far, 0, results, &resultsLength, eligibleCharacters);
    free(nodes);
    return results;
}

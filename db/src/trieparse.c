#include "trieparse.h"
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

void searchTrie(const char* base, long offset, char word_so_far[32],
    int word_so_far_length, char* results, int* results_length,
    const char* eligible_indexes)
{
    const struct TrieHeader* current = (struct TrieHeader*)(base + offset);
    if (current->completes_word && word_so_far_length > 3) {
        strcpy(results + *results_length, word_so_far);
        *results_length += strlen(word_so_far);
        results[*results_length] = ' ';
        results[(*results_length) + 1] = '\0';
        *results_length += 1;
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
                    word_so_far_length + 1, results, results_length,
                    eligible_indexes);
            }
        }
    }
}

const char* search_words(
    const char* trie_buffer, const char* eligible_characters)
{
    char* results = malloc(10000);
    char word_so_far[32];
    word_so_far[0] = 0;
    int results_length = 0;
    searchTrie(trie_buffer, 0, word_so_far, 0, results, &results_length,
        eligible_characters);
    return results;
}

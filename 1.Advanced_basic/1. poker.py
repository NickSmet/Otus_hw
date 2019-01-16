#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# 'C','S','H','D'



# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета, в колоде два джокерва.
# Черный джокер '?B' может быть использован в качестве треф
# или пик любого ранга, красный джокер '?R' - в качестве черв и бубен
# любого ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertoolsю
# Можно свободно определять свои функции и т.п.
# -----------------

from itertools import combinations

ranks=['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
black_suits=['C','S']
red_suits=['H','D']
jokers=['?B','?R']
black_joker=[rank + suit for rank in ranks for suit in black_suits]
red_joker=[rank+suit for rank in ranks for suit in red_suits]


def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    ranks = card_ranks(hand)

    if straight(ranks) and flush(hand):
        return (8, max(ranks))
    elif kind(4, ranks):
        return (7, kind(4, ranks), kind(1, ranks))
    elif kind(3, ranks) and kind(2, ranks):
        return (6, kind(3, ranks), kind(2, ranks))
    elif flush(hand):
        return (5, ranks)
    elif straight(ranks):
        return (4, max(ranks))
    elif kind(3, ranks):
        return (3, kind(3, ranks), ranks)
    elif two_pair(ranks):
        return (2, two_pair(ranks), ranks)
    elif kind(2, ranks):
        return (1, kind(2, ranks), ranks)
    else:
        return (0, ranks)

def card_ranks(hand):
    """Возвращает список рангов (его числовой эквивалент),
    отсортированный от большего к меньшему"""
    rank_dict = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    card_ranks=[x[0] for x in hand]
    ranks=[]
    for i in card_ranks:
        try:
            ranks.append(int(i))
        except:
            ranks.append(rank_dict[i])
    return sorted(ranks,reverse=True)

def flush(hand):
    """Возвращает True, если все карты одной масти"""
    return len(set(card[1] for card in hand))==1

def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    return ranks == list(range(max(ranks),min(ranks)-1,-1))

def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""
    for i in ranks:
        if ranks.count(i)==n:
            return i
    return None

def two_pair(ranks):
    """Если есть две пары, то возврщает два соответствующих ранга,
    иначе возвращает None"""
    uniques=set(ranks)
    if 2<=len(uniques)<=3:
        """Т.к. у нас 5 карт, то наличие 2-х пар означает 2 или 3 уникальных ранга"""
        pair_ranks=[i for i in uniques if ranks.count(i)>=2]
        return pair_ranks
    else:
        return None

def best_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт """
    return max(combinations(hand,5), key=hand_rank)

def best_wild_hand(hand):
    """best_hand но с джокерами"""
    alternatives=get_alternatives(hand)
    best_hands=[best_hand(hand) for hand in alternatives]
    return max(best_hands, key=hand_rank)

def get_alternatives(hand):
    """Принимает руку из 7 карт и возвоащает список рук, которому рука эквивалентна.
    Если в руке нет джокеров, возвращает список с одной, исходной рукой"""

    jokerless=[card for card in hand if card not in jokers]

    """Т.к. джокер не может принимать значение уже имеющихся в руке карт (возможно, стоит эксплицировать это в задании),
    убираем их из возможных значений джокеров"""
    bjk_possible = [card for card in black_joker if card not in jokerless]
    rjk_possible = [card for card in red_joker if card not in jokerless]

    if all(joker in hand for joker in jokers):
        alternatives=[jokerless+[bjk]+[rjk] for bjk in bjk_possible for rjk in rjk_possible]
    elif '?B' in hand:
        alternatives=[jokerless+[bjk] for bjk in bjk_possible]
    elif '?R' in hand:
        alternatives=[jokerless+[rjk] for rjk in rjk_possible]
    else:
        alternatives=[hand]
    return alternatives

def test_best_hand():
    print ("test_best_hand...")
    assert (sorted(best_hand("6C 7C 8C 9C TC 5C JS".split()))
            == ['6C', '7C', '8C', '9C', 'TC'])
    assert (sorted(best_hand("TD TC TH 7C 7D 8C 8S".split()))
            == ['8C', '8S', 'TC', 'TD', 'TH'])
    assert (sorted(best_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print ('OK')

def test_best_wild_hand():
    print ("test_best_wild_hand...")
    assert (sorted(best_wild_hand("6C 7C 8C 9C TC 5C ?B".split()))
            == ['7C', '8C', '9C', 'JC', 'TC'])
    assert (sorted(best_wild_hand("TD TC 5H 5C 7C ?R ?B".split()))
            == ['7C', 'TC', 'TD', 'TH', 'TS'])
    assert (sorted(best_wild_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print ('OK')

if __name__ == '__main__':
    test_best_hand()
    test_best_wild_hand()

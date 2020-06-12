from edict.utils import OrderedSet


def test_ordered_set_init_empty():
    s = OrderedSet()
    assert list(s) == []


def test_ordered_set_init_elems():
    s = OrderedSet(range(3))
    assert list(s) == [0, 1, 2]


def test_ordered_set_eq_true():
    assert OrderedSet() == OrderedSet()
    assert OrderedSet(range(2)) == OrderedSet(range(2))


def test_ordered_set_eq_shuffle():
    # Follows dict semantics where different orders comapre equal
    assert OrderedSet([1, 2]) == OrderedSet([2, 1])


def test_ordered_set_eq_false():
    assert not OrderedSet() == OrderedSet([1])
    assert not OrderedSet(range(2)) == OrderedSet(range(1, 3))


def test_ordered_set_neq_true():
    assert OrderedSet() != OrderedSet([1])
    assert OrderedSet(range(2)) != OrderedSet(range(1, 3))


def test_ordered_set_contains():
    s = OrderedSet(range(3))
    assert 0 in s
    assert 3 not in s
    assert "foo" not in s


def test_ordered_set_iter():
    s = OrderedSet(range(3))
    assert list(iter(s)) == [0, 1, 2]


def test_ordered_set_len_empty():
    s = OrderedSet()
    assert len(s) == 0


def test_ordered_set_len_nonempty():
    s = OrderedSet(range(3))
    assert len(s) == 3
    s.add(3)
    assert len(s) == 4


def test_ordered_set_add():
    s = OrderedSet()
    s.add(3)
    s.add(0)
    assert list(s) == [3, 0]
    assert s == OrderedSet([3, 0])


def test_ordered_set_add_repeats():
    s = OrderedSet([1])
    s.add(2)
    s.add(2)
    s.add(1)
    assert len(s) == 2
    assert list(s) == [1, 2]


def test_ordered_set_update():
    s = OrderedSet([3, 2, 1])
    s.update([2, 3, 4])
    assert s == OrderedSet([3, 2, 1, 4])


def test_ordered_set_clear():
    s = OrderedSet([1, 2])
    s.clear()
    assert s == OrderedSet()
    s.update([2, 3])
    assert s == OrderedSet([2, 3])


def test_ordered_set_order():
    s = OrderedSet(reversed(range(3)))
    assert list(s) == [2, 1, 0]
    s.add(-1)
    s.add(4)
    assert list(s) == [2, 1, 0, -1, 4]

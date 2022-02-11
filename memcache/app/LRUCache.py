from app import cache, memcache
from sys import getsizeof


class DLinkedNode:
    def __init__(self, key='', value=''):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache:

    def __init__(self, capacity: int):
        # self.cache = dict()
        # 使用伪头部和伪尾部节点
        self.head = DLinkedNode()
        self.tail = DLinkedNode()
        self.head.next = self.tail
        self.tail.prev = self.head
        self.capacity = capacity
        self.size = 0

    def setCapacity(self, cap: int):
        self.capacity = cap

    def getCapacity(self):
        return self.capacity

    def getLRU(self, key: str) -> int:
        if key not in cache:
            return -1
        # 如果 key 存在，先通过哈希表定位，再移到头部
        node = cache[key]
        self.moveToHead(node)
        return node.value

    def put(self, key: str, value: str) -> None:
        if key not in cache:
            # 如果 key 不存在，创建一个新的节点
            node = DLinkedNode(key, value)
            # 添加进哈希表
            cache[key] = node
            # 添加至双向链表的头部
            self.addToHead(node)
            # self.size += 1
            new_cap = getsizeof(key) + getsizeof(value)
            print(self.cal() + new_cap/1024)
            while self.cal() + new_cap/1024> self.getCapacity():
                print("size", self.cal())
                print("self.capacity", self.getCapacity())
                # 如果超出容量，删除双向链表的尾部节点
                removed = self.removeTail()
                # 删除哈希表中对应的项
                print(memcache)
                cache.pop(removed.key)
                memcache.pop(removed.key)

                # self.size -= 1
            # self.size +=(getsizeof(key) + getsizeof(value))
        else:
            # 如果 key 存在，先通过哈希表定位，再修改 value，并移到头部
            node = cache[key]
            node.value = value
            self.moveToHead(node)

    def deleteNode(self):
        # total=self.cal()
        while self.cal() > self.capacity:
            print("in delete", self.capacity)
            removed = self.removeTail()
            # 删除哈希表中对应的项
            cache.pop(removed.key)
            memcache.pop(removed.key)

    def findNode(self, key):
        node = cache[key]
        self.removeNode(node)

    def addToHead(self, node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def removeNode(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def moveToHead(self, node):
        self.removeNode(node)
        self.addToHead(node)

    def removeTail(self):
        node = self.tail.prev
        self.removeNode(node)
        return node

    def clear(self):
        for key in cache:
            node = cache[key]
            self.removeNode(node)

    def cal(self):
        size = 0
        for k in memcache.keys():
            size += getsizeof(k)
        for k in memcache.values():
            size += getsizeof(k)

        return size/1024

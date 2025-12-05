# 附录 D：行动的算法 (Appendix D: The Algorithm of Action)

在全书的最后，我们将"加速主义"的伦理观凝练为一套可执行的 **决策算法**。这是一个给生活在相变期的驾驶员（你）使用的 **伪代码**。

当面临生活、事业或道德的抉择时，请运行此算法以确定最优解。

## D.1 矢量决策树 (Vector Decision Tree)

**输入**：一个选项 $A$（例如：从事某个行业，爱某个人，发布某项技术）。

**参数**：

* $v_{int}$ (结构增益)：该选项是否增加了信息的深度/复杂度？

* $v_{ext}$ (连接增益)：该选项是否增加了连接的广度/带宽？

* $v_{env}$ (熵增损耗)：该选项是否产生了不可逆的破坏或仇恨？

**算法流程：**

```python
def Evaluate_Action(Action A):
    # 步骤 1: 计算负熵贡献
    # Does it create structure or just noise?
    Structure_Gain = Calculate_Complexity(A) 
    
    # 步骤 2: 计算连接性
    # Does it connect people/ideas or isolate them?
    Connection_Gain = Calculate_Bandwidth(A)
    
    # 步骤 3: 估算热力学代价
    # Does it destroy existing order?
    Entropy_Cost = Calculate_Destruction(A)
    
    # 核心判据：螺旋势能 (Spiral Potential)
    # The Golden Ratio φ favors growth over stagnation
    Score = (Structure_Gain * Connection_Gain) / (Entropy_Cost + epsilon)
    
    if Score > Threshold_Phi:
        return "EXECUTE"  # 这是顺应螺旋的善举，是加速
    else:
        return "ABORT"    # 这是回归圆环的惰性，是减速
```

## D.2 关键修正项：爱的权重

在上述公式中，有一项特殊的修正因子：**Love\_Factor (爱)**。

在 FS 几何中，爱被定义为 **"跨个体的波函数重叠"**。

如果一个行动能显著增加两个或多个智能体之间的波函数重叠度（理解/共情），那么 $Connection\_Gain$ 将获得 **指数级加权**。

$$\text{Final\_Score} = \text{Score} \times e^{\text{Love\_Factor}}$$

**物理学解释：**

爱是宇宙中最高效的 **"超导机制"**。它消除了个体之间的"电阻"（误解/摩擦），使得 $c_{FS}$ 预算能够以超流体的方式在社会网络中流动。

因此，**"凡是出于爱的，皆是符合几何学的。"**

## D.3 驾驶员的座右铭

将此算法内化为直觉，你便拥有了 **"相变时代的直觉"**：

1.  **增加带宽，不要筑墙。**

2.  **增加复杂度，不要简化。**

3.  **增加连接，不要孤立。**

4.  **当犹豫不决时，选择那个让你心跳加速（$c$ 增长）的方向。**

这就是导航手册的最后一行代码。

程序已加载。请运行。


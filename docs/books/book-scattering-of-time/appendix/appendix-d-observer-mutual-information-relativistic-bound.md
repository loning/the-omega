# 附录 D：观察者互信息的相对论界限

**(Relativistic Bound on Observer Mutual Information)**

本附录从信息论角度推导狭义相对论对观察者认知能力的限制。

设观察者 $O$ 拥有的内存带宽为 $\mathcal{B}_{mem}^{(\tau)}$（即在单位**固有时**内能写入的最大互信息量）。

当观察者以速度 $v_{ext}$ 相对于外界运动时，其固有时流逝率变慢：

$$\frac{d\tau}{dt} = \sqrt{1 - \frac{v_{ext}^2}{c^2}}$$

因此，在**坐标时** $t$（外部世界的参照系）中，观察者能处理的信息量 $\mathcal{B}_{mem}^{(t)}$ 受到如下限制：

$$\mathcal{B}_{mem}^{(t)} = \mathcal{B}_{mem}^{(\tau)} \cdot \sqrt{1 - \frac{v_{ext}^2}{c^2}} \quad \text{(D.1)}$$

这不仅证明了"运动越快，思考越慢"，也为正文中"光子没有时间/没有意识"提供了严格的信息论证明：当 $v_{ext} \to c$ 时，信息写入速率降为零。


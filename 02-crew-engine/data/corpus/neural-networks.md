# How Neural Networks Actually Work

A neural network is a function that turns inputs into outputs, tuned by
training data. Architecturally it is a stack of layers, each made of
neurons (small math units). Every neuron multiplies its inputs by weights,
adds a bias, and passes the result through an activation function such as
ReLU, which turns negatives to zero.

Training is the core idea. Given labeled examples, the network makes a
prediction, compares it to the true answer with a loss function, then
adjusts weights using backpropagation — the chain rule of calculus applied
backward through the network. Repeating this over many batches slowly
steers the network toward correct answers.

Two extensions made modern networks practical. First, convolution layers
share weights across a sliding window, which makes image models far more
data-efficient. Second, transformers replaced position-by-position
recurrence with attention, letting models look at an entire sentence at
once and decide which words deserve the most weight.

Networks learn patterns that are hard for humans to name: edges in early
image layers, whole objects in later ones; syntax in early language layers,
meaning in later ones. But they have limits: they memorize data they have
seen, they are sensitive to how data is prepared, and they often need
enormous amounts of clean training data to behave well.
def test_all_captial(token):
	all_caps = True
	for l in token:
		if not l.isupper():
			all_caps = False
			break
	return all_caps

def test_first_capital(token):
	return token[0].isupper()

def test_all_digit(token):
	all_digit = True
	for l in token:
		if not l.isdigit():
			all_digit = False
			break
	return all_digit

def test_contain_digit(token):
	contain_digit = False
	for l in token:
		if l.isdigit():
			contain_digit = True
			break
	return contain_digit

def get_word_shape(token):
	shape = []
	for c in token:
		if c.isalpha():
			if c.isupper():
				shape.append("X")
			else:
				shape.append("x")
		elif c.isdigit():
			shape.append("d")
		else:
			shape.append(c)
	suffix = []
	if len(token) > 2:
		suffix = shape[-2:]
	elif len(token) > 1:
		suffix = shape[-1:]

	middle = []
	if len(shape) > 3:
		c = shape[1]
		i = 1
		while i < len(shape) - 2:
			middle.append(c)
			while c == shape[i] and i < len(shape) -2:
				i += 1
			c = shape[i]

		if c != middle[-1]:
			middle.append(c)

	return (shape[0] + middle + suffix).join("")

def dehyphenize(text):
	res = ""
	
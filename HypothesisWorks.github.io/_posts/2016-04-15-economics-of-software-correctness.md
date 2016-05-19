---
layout: post
tags: writing-good-software non-technical
date: 2016-04-15 15:00
title: The Economics of Software Correctness
published: true
author: drmaciver
---------

You have probably never written a significant piece of correct software.

That's not a value judgement. It's certainly not a criticism of your competence. I can say with almost complete confidence that every non-trivial piece of software I have written contains at least one bug. You *might* have written small libraries that are essentially bug free, but the chance that you have written a non-trivial bug free program is tantamount to zero.

I don't even mean this in some pedantic academic sense. I'm talking about behaviour where if someone spotted it and pointed it out to you you would probably admit that it's a bug. It might even be a bug that you cared about.

Why is this?

<!--more-->

Well, lets start with why it's not: It's not because we don't know how to write correct software. We've known how to write software that is more or less correct (or at least vastly closer to correct than the norm) for a while now. If you <a href="http://www.fastcompany.com/28121/they-write-right-stuff">look at the NASA development process</a> they're pretty much doing it.

Also, if you look at the NASA development process you will probably conclude that we can't do that. It's orders of magnitude more work than we ever put into software development. It's process heavy, laborious, and does not adapt well to changing requirements or tight deadlines.

The problem is not that we don't know how to write correct software. The problem is that correct software is too expensive.

And "too expensive" doesn't mean "It will knock 10% off our profit margins, we couldn't possibly do that". It means "if our software cost this much to make, nobody would be willing to pay a price we could afford to sell it at". It may also mean "If our software took this long to make then someone else will release a competing product two years earlier than us, everyone will use that, and when ours comes along nobody will be interested in using it".

("sell" and "release" here can mean a variety of things. It can mean that terribly unfashionable behaviour where people give you money and you give them a license to your software. It can mean subscriptions. It can mean ad space. It can even mean paid work. I'm just going to keep saying sell and release).

NASA can do it because when they introduce a software bug they potentially lose some combination of billions of dollars, years of work and many lives. When that's the cost of a bug, spending that much time and money on correctness seems like a great deal. Safety critical industries like medical technology and aviation can do it for similar reasons
([buggy medical technology kills people](https://en.wikipedia.org/wiki/Therac-25) and [you don't want your engines power cycling themselves midflight](http://www.engadget.com/2015/05/01/boeing-787-dreamliner-software-bug/)).

The rest of us aren't writing safety critical software, and as a result people aren't willing to pay for that level of correctness.

So the result is that we write software with bugs in it, and we adopt a much cheaper software testing methodology: We ship it and see what happens. Inevitably some user will find a bug in our software. Probably many users will find many bugs in our software.

And this means that we're turning our users into our QA department.

Which, to be clear, is fine. Users have stated the price that they're willing to pay, and that price does not include correctness, so they're getting software that is not correct. I think we all feel bad about shipping buggy software, so let me emphasise this here: Buggy software is not a moral failing. The option to ship correct software is simply not on the table, so why on earth should we feel bad about not taking it?

But in another sense, turning our users into a QA department is a terrible idea.

Why? Because users are not actually good at QA. QA is a complicated professional skill which very few people can do well. Even skilled developers often don't know <a href="http://www.drmaciver.com/2013/09/how-to-submit-a-decent-bug-report/">how to write a good bug report</a>. How can we possibly expect our users to?

The result is long and frustrating conversations with users in which you try to determine whether what they're seeing is actually a bug or a misunderstanding (although treating misunderstandings as bugs is a good idea too), trying to figure out what the actual bug is, etc. It's a time consuming process which ends up annoying the user and taking up a lot of expensive time from developers and customer support.

And that's of course if the users tell you at all. Some users will just try your software, decide it doesn't work, and go away without ever saying anything to you. This is particularly bad for software where you can't easily tell who is using it.

Also, some of our users are actually adversaries. They're not only not going to tell you about bugs they find, they're going to actively try to keep you from finding out because they're using it to steal money and/or data from you.

So <em>this</em> is the problem with shipping buggy software: Bugs found by users are more expensive than bugs found before a user sees them. Bugs found by users may result in lost users, lost time and theft. These all hurt the bottom line.

At the same time, your users are a lot more effective at finding bugs than you are due to sheer numbers if nothing else, and as we've established it's basically impossible to ship fully correct software, so we end up choosing some level of acceptable defect rate in the middle. This is generally determined by the point at which it is more expensive to find the next bug yourself than it is to let your users find it. Any higher or lower defect rate and you could just adjust your development process and make more money, and companies like making money so if they're competently run will generally do the things that cause them to do so.

You can, and should, [cheaper to find bugs is to reduce the cost of when your users do find them](http://itamarst.org/softwaretesting/book/realworld.html), but it's always going to be expensive.

This means that there are only two viable ways to improve software quality:

* Make users angrier about bugs
* Make it cheaper to find bugs

I think making users angrier about bugs is a good idea and I wish people cared more about software quality, but as a business plan it's a bit of a rubbish one. It creates higher quality software by making it more expensive to write software.

Making it cheaper to find bugs though... that's a good one, because it increases the quality of the software by increasing your profit margins. Literally everyone wins: The developers win, the users win, the business's owners win.

And so this is the lever we get to pull to change the world: If you want better software, make or find tools that reduce the effort of finding bugs.

Obviously I think Hypothesis is an example of this, but it's neither the only one nor the only one you need. Better monitoring is another. Code review processes. Static analysis. Improved communication. There are many more.

But one thing that *won't* improve your ability to find bugs is feeling bad about yourself and trying really hard to write correct software then feeling guilty when you fail. This seems to be the current standard, and it's deeply counter-productive. You can't fix systemic issues with individual action, and the only way to ship better software is to change the economics to make it viable to do so.

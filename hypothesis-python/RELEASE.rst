RELEASE_TYPE: patch

This patch clarifies the reporting of time spent generating data. A
simple arithmetic mean of the percentage of time spent can be
misleading; reporting the actual time spent avoids misunderstandings.

Thanks to Andrea Reina for reporting and fixing :issue:`3598`!

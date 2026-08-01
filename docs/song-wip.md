# Song converter (`d20-tools song`) — work in progress

Song files use the `.222` extension. The command reserves a stable public
interface for future support, but deliberately performs no conversion in
version 0.2 and exits with a clear WIP message.

`d20-tools inspect INPUT` already identifies a native Song container from its
validated structure, including its embedded Rhythm section, rather than from
its filename extension. It lists the embedded Rhythm Setup, Pattern, Track,
and Sequencer Header as 78 DT1-equivalent messages. The Song's real-time event
stream has no DT1-memory equivalent and is not converted yet.

Song conversion needs separate treatment for the real-time note tracks and the
rhythm-pattern chain. It will not be released until both can be validated
without altering the source file.

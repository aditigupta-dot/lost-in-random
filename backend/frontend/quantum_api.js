export async function checkQuantum(answer){
    const res = await fetch("http://localhost:5000/check",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({answer})
    });

    return await res.json();
}